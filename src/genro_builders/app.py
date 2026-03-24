# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BagAppBase — reactive application runtime for genro-builders.

Coordinates the 4-stage pipeline:
    1. Source Bag (recipe with builder, components, ^pointers)
    2. Compiled Bag (components expanded, pointers resolved, map registered)
    3. Bound Bag (subscriptions active, reactive updates)
    4. Output (rendered by compiler)

Compilation is a single recursive walk (_compile_bag) that for each node:
    1. Expands components (via resolver)
    2. Resolves ^pointers against data
    3. Registers subscriptions in the binding map

The same method handles full compile and incremental compile on subtrees.

Reactivity:
    - Source change → incremental compile on subtree
    - Data change → subscription updates nodes → re-render
    - Recipe change → full rebuild()

Bag shells:
    Both source and compiled bags are wrapped in a shell Bag with backref
    enabled. This ensures parent-child relationships are maintained from
    the start, enabling datapath resolution and event propagation.

Example:
    >>> class MyApp(BagAppBase):
    ...     builder_class = HtmlBuilder
    ...
    ...     def recipe(self, source):
    ...         source.h1(value='^page.title')
    ...         source.p(value='^content.text')
    ...
    >>> app = MyApp()
    >>> app.data['page.title'] = 'Hello'
    >>> app.data['content.text'] = 'World'
    >>> app.setup()
    >>> print(app.output)
"""
from __future__ import annotations

from typing import Any

from genro_bag import Bag, BagNode

from .binding import BindingManager
from .builder_bag import BuilderBag
from .compiler import BagCompilerBase
from .pointer import scan_for_pointers


class BagAppBase:
    """Base class for reactive Bag applications.

    Subclasses must set ``builder_class`` and override ``recipe()``.
    Optionally set ``compiler_class`` (falls back to builder's _compiler_class).

    Lifecycle:
        1. __init__: create source, data, compiled shells, binding, compiler
        2. recipe(source): populate the source bag (override in subclass)
        3. setup(): call recipe + compile + enable auto-compile
        4. Data changes trigger partial re-render automatically
        5. Source changes trigger incremental compile automatically
        6. rebuild(): full rebuild on recipe change
    """

    builder_class: type
    compiler_class: type | None = None

    def __init__(self) -> None:
        """Initialize the app. Does NOT call recipe() yet."""
        # Source shell: backref-enabled wrapper for the recipe bag
        self._source_shell = BuilderBag(builder=self.builder_class)
        self._source_shell.set_backref()
        self._source_shell.set_item("root", BuilderBag(builder=self.builder_class))

        # Compiled shell: backref-enabled wrapper for the compiled bag
        self._compiled_shell = BuilderBag(builder=self.builder_class)
        self._compiled_shell.set_backref()
        self._compiled_shell.set_item("root", BuilderBag(builder=self.builder_class))

        # Data bag
        self._data = Bag()
        self._data.set_backref()

        self._binding = BindingManager(on_node_updated=self._on_node_updated)
        self._auto_compile = False
        self._output: str | None = None

        compiler_cls = self.compiler_class or getattr(self.builder_class, "_compiler_class", None)
        if compiler_cls:
            self._compiler: BagCompilerBase | None = compiler_cls(self.source.builder)
        else:
            self._compiler = None

    @property
    def source(self) -> BuilderBag:
        """The source Bag (recipe). Backref-enabled via shell."""
        return self._source_shell.get_item("root")

    @property
    def compiled(self) -> BuilderBag:
        """The compiled Bag (components expanded, pointers resolved). Backref-enabled via shell."""
        return self._compiled_shell.get_item("root")

    @property
    def data(self) -> Bag:
        """The data Bag. Setting values triggers reactive updates."""
        return self._data

    @data.setter
    def data(self, value: Bag | dict[str, Any]) -> None:
        """Replace the data Bag entirely. Triggers full rebind + recompile."""
        new_data = Bag(source=value) if isinstance(value, dict) else value

        if not new_data.backref:
            new_data.set_backref()

        self._data = new_data

        if self._auto_compile:
            self._binding.rebind(new_data)
            self._rerender()

    @property
    def output(self) -> str | None:
        """Last compiled output."""
        return self._output

    def setup(self) -> None:
        """Call recipe() and do initial compile.

        After setup, data changes trigger automatic re-compilation.
        """
        self.recipe(self.source)
        self.compile()
        self._auto_compile = True

    def recipe(self, source: BuilderBag) -> None:
        """Template method: populate the source with builder calls.

        Override in subclass:
            def recipe(self, source):
                source.div(id='main')
                source.p(value='^content.text')
        """

    def compile(self) -> str:
        """Full pipeline: compile (materialize + resolve + register) → subscribe → render.

        Returns:
            Compiled output string.

        Raises:
            RuntimeError: If no compiler is configured.
        """
        if self._compiler is None:
            raise RuntimeError(
                f"{type(self).__name__} has no compiler. "
                f"Set compiler_class on the app or builder."
            )

        # 1. Clear compiled bag and binding map
        self._clear_compiled()

        # 2. Compile: materialize + resolve pointers + register in map
        self._compile_bag(self.source, self.compiled)

        # 3. Subscribe to data changes for reactive updates
        self._binding.subscribe(self.compiled, self._data)

        # 4. Subscribe to source changes for incremental updates
        self.source.subscribe(
            "source_watcher",
            delete=self._on_source_deleted,
            insert=self._on_source_inserted,
            update=self._on_source_updated,
        )

        # 5. Render
        self._output = self.render(self.compiled)
        return self._output

    # -------------------------------------------------------------------------
    # Compilation: single recursive walk
    # -------------------------------------------------------------------------

    def _compile_bag(
        self, source: Bag, target: Bag, prefix: str = "",
    ) -> None:
        """Compile source into target: materialize + resolve pointers + register map.

        Recursive: for each node, expands components, resolves ^pointers,
        registers subscriptions, then recurses into children.

        Used for both full compile and incremental compile on subtrees.

        Args:
            source: The source Bag to compile from.
            target: The compiled Bag to populate.
            prefix: Path prefix for subscription map registration.
        """
        for node in source:
            # Expand component if resolver present
            value = node.get_value(static=False) if node.resolver is not None else node.static_value

            # Insert into compiled bag
            new_node = target.set_item(
                node.label,
                value if not isinstance(value, Bag) else BuilderBag(builder=self.builder_class),
                _attributes=dict(node.attr),
                node_tag=node.node_tag,
            )

            compiled_path = f"{prefix}.{node.label}" if prefix else node.label

            # Resolve ^pointers and register in map
            self._resolve_and_register(new_node, compiled_path)

            # Recurse into children
            if isinstance(value, Bag):
                self._compile_bag(value, new_node.value, prefix=compiled_path)

    def _compile_node(
        self, node: BagNode, target: Bag, path: str, ind: int | None = None,
    ) -> None:
        """Compile a single source node into target (incremental).

        Same logic as _compile_bag but for a single node + children.

        Args:
            node: The source BagNode to compile.
            target: The target Bag to insert into.
            path: The compiled path for this node.
            ind: Optional position index for insertion.
        """
        value = node.get_value(static=False) if node.resolver is not None else node.static_value

        new_node = target.set_item(
            node.label,
            value if not isinstance(value, Bag) else BuilderBag(builder=self.builder_class),
            _attributes=dict(node.attr),
            node_position=ind,
            _reason="source",
            node_tag=node.node_tag,
        )

        self._resolve_and_register(new_node, path)

        if isinstance(value, Bag):
            self._compile_bag(value, new_node.value, prefix=path)

    def _resolve_and_register(self, node: BagNode, compiled_path: str) -> None:
        """Resolve ^pointers on a node and register subscriptions in the map.

        Args:
            node: The compiled BagNode to process.
            compiled_path: The absolute path of this node in the compiled bag.
        """
        pointers = scan_for_pointers(node)
        if not pointers:
            return

        for pointer_info, location in pointers:
            # Resolve datapath for relative pointers
            datapath = ""
            if pointer_info.is_relative and hasattr(node, "_resolve_datapath"):
                datapath = node._resolve_datapath()

            # Compute absolute data path
            data_path = pointer_info.path
            if pointer_info.is_relative:
                rel = data_path[1:]  # strip leading '.'
                data_path = f"{datapath}.{rel}" if datapath else rel

            # Resolve value from data and apply
            resolved = self._resolve_pointer(node, pointer_info, data_path, datapath)
            if location == "value":
                node.set_value(resolved, trigger=False)
            elif location.startswith("attr:"):
                attr_name = location[5:]
                node.set_attr({attr_name: resolved}, trigger=False)

            # Build map keys and register
            data_key = f"{data_path}?{pointer_info.attr}" if pointer_info.attr else data_path
            compiled_entry = compiled_path if location == "value" else f"{compiled_path}?{location[5:]}"

            self._binding.register(data_key, compiled_entry)

    def _resolve_pointer(
        self, node: BagNode, pointer_info: Any, data_path: str, datapath: str,
    ) -> Any:
        """Resolve a single ^pointer value from the data Bag."""
        if hasattr(node, "_get_relative_data"):
            return node._get_relative_data(self._data, pointer_info.raw[1:])  # strip ^

        if pointer_info.attr:
            data_node = self._data.get_node(data_path)
            return data_node.attr.get(pointer_info.attr) if data_node else None
        return self._data.get_item(data_path)

    # -------------------------------------------------------------------------
    # Lifecycle helpers
    # -------------------------------------------------------------------------

    def _clear_compiled(self) -> None:
        """Clear the compiled bag without destroying the shell."""
        self._binding.unbind()
        new_root = BuilderBag(builder=self.builder_class)
        self._compiled_shell.set_item("root", new_root)

    def _clear_source(self) -> None:
        """Clear the source bag without destroying the shell."""
        new_root = BuilderBag(builder=self.builder_class)
        self._source_shell.set_item("root", new_root)
        if self._compiler is not None:
            self._compiler.builder = self.source.builder

    def rebuild(self) -> str:
        """Full rebuild: clear source, re-run recipe, compile.

        Use when the recipe itself has changed.

        Returns:
            Compiled output string.
        """
        self.source.unsubscribe("source_watcher", any=True)
        self._auto_compile = False

        self._clear_source()
        self.recipe(self.source)
        result = self.compile()
        self._auto_compile = True
        return result

    def render(self, compiled_bag: Bag) -> str:
        """Render a CompiledBag to output string.

        Delegates to compiler.render() if available, otherwise
        uses compiler's _walk_compile + join as fallback.
        Override in subclass for custom rendering.

        Args:
            compiled_bag: The compiled Bag (components expanded, pointers resolved).

        Returns:
            Rendered output string.
        """
        if self._compiler is None:
            raise RuntimeError(f"{type(self).__name__} has no compiler for rendering.")
        if hasattr(self._compiler, "render"):
            return self._compiler.render(compiled_bag)
        parts = list(self._compiler._walk_compile(compiled_bag))
        return "\n\n".join(p for p in parts if p)

    def _on_node_updated(self, node: BagNode) -> None:
        """Called by BindingManager when a bound node is updated.

        Triggers re-render of the compiled bag.
        """
        if self._auto_compile:
            self._rerender()

    # -------------------------------------------------------------------------
    # Source change handlers (incremental compile)
    # -------------------------------------------------------------------------

    def _on_source_deleted(
        self,
        node: BagNode | None = None,
        pathlist: list | None = None,
        ind: int | None = None,
        evt: str = "",
        **kwargs: Any,
    ) -> None:
        """Called when a node is deleted from the source.

        Removes the corresponding node from the compiled bag,
        cleans up bindings, and re-renders.
        """
        if not self._auto_compile or node is None:
            return
        parts = [str(p) for p in pathlist] if pathlist else []
        parts.append(node.label)
        path = ".".join(parts)
        self._binding.unbind_path(path)
        self.compiled.del_item(path, _reason="source")
        self._rerender()

    def _on_source_inserted(
        self,
        node: BagNode | None = None,
        pathlist: list | None = None,
        ind: int | None = None,
        evt: str = "",
        **kwargs: Any,
    ) -> None:
        """Called when a node is inserted into the source.

        Compiles the new node (materialize + resolve + register) and re-renders.
        """
        if not self._auto_compile or node is None:
            return
        if self._compiler is None:
            return

        parent_path = ".".join(str(p) for p in pathlist) if pathlist else ""

        if parent_path:
            target_bag = self.compiled.get_item(parent_path)
            if not isinstance(target_bag, Bag):
                return
        else:
            target_bag = self.compiled

        node_path = f"{parent_path}.{node.label}" if parent_path else node.label
        self._compile_node(node, target_bag, node_path, ind=ind)

        self._rerender()

    def _on_source_updated(
        self,
        node: BagNode | None = None,
        pathlist: list | None = None,
        oldvalue: Any = None,
        evt: str = "",
        **kwargs: Any,
    ) -> None:
        """Called when a node in the source is updated (value or attributes).

        Cleans up old bindings, recompiles the node, and re-renders.
        """
        if not self._auto_compile or pathlist is None:
            return
        if self._compiler is None:
            return

        path = ".".join(str(p) for p in pathlist)
        compiled_node = self.compiled.get_node(path)
        if compiled_node is None:
            return

        if evt == "upd_value":
            value = node.get_value(static=False) if node.resolver is not None else node.static_value

            # Clean up old bindings for this subtree
            self._binding.unbind_path(path)

            if isinstance(value, Bag):
                # Replace with empty bag, then compile children into it
                compiled_node.set_value(BuilderBag(builder=self.builder_class), _reason="source")
                self._resolve_and_register(compiled_node, path)
                self._compile_bag(value, compiled_node.value, prefix=path)
            else:
                compiled_node.set_value(value, _reason="source")
                self._resolve_and_register(compiled_node, path)

        elif evt == "upd_attrs":
            if node is not None:
                compiled_node.set_attr(dict(node.attr))
                self._binding.unbind_path(path)
                self._resolve_and_register(compiled_node, path)

        self._rerender()

    def _rerender(self) -> None:
        """Re-render the compiled bag without re-compiling.

        Used after data changes — nodes are already updated by binding.
        """
        self._output = self.render(self.compiled)
