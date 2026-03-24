# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BagAppBase — reactive application runtime for genro-builders.

Coordinates the 4-stage pipeline:
    1. Source Bag (recipe with builder, components, ^pointers)
    2. Compiled Bag (components expanded via _materialize)
    3. Bound Bag (^pointers resolved, subscriptions active)
    4. Output (rendered by compiler)

Reactivity:
    - Source change → incremental compile (insert/delete/update)
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


class BagAppBase:
    """Base class for reactive Bag applications.

    Subclasses must set ``builder_class`` and override ``recipe()``.
    Optionally set ``compiler_class`` (falls back to builder's compiler_class).

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

        compiler_cls = self.compiler_class or getattr(self.builder_class, "compiler_class", None)
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
        """Full pipeline: materialize → bind → render.

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

        # 1. Clear and repopulate compiled bag
        self._clear_compiled()
        self._compiler.compile(self.source, target=self.compiled)

        # 2. Bind: resolve pointers + register subscriptions for reactive updates
        self._binding.bind(self.compiled, self._data)

        # 3. Subscribe to source changes for incremental updates
        self.source.subscribe(
            "source_watcher",
            delete=self._on_source_deleted,
            insert=self._on_source_inserted,
            update=self._on_source_updated,
        )

        # 4. Render
        self._output = self.render(self.compiled)
        return self._output

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

        Materializes the new node, inserts it into the compiled bag
        at the same position, binds ^pointers, and re-renders.
        """
        if not self._auto_compile or node is None:
            return
        if self._compiler is None:
            return

        # Determine the parent path in the compiled bag
        parent_path = ".".join(str(p) for p in pathlist) if pathlist else ""

        # Materialize the new node's value
        value = node.get_value(static=False) if node.resolver is not None else node.static_value
        if isinstance(value, Bag):
            value = self._compiler._materialize(value)

        # Find the target bag in the compiled tree
        if parent_path:
            target_bag = self.compiled.get_item(parent_path)
            if not isinstance(target_bag, Bag):
                return
        else:
            target_bag = self.compiled

        # Insert the materialized node at the same position
        new_node = target_bag.set_item(
            node.label,
            value,
            _attributes=dict(node.attr),
            node_position=ind,
            _reason="source",
            node_tag=node.node_tag,
        )

        # Bind ^pointers on the new subtree
        node_path = f"{parent_path}.{node.label}" if parent_path else node.label
        self._binding.bind_subtree(new_node, self._data, node_path)

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

        Updates the corresponding node in the compiled bag,
        re-binds ^pointers if needed, and re-renders.
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
            # Materialize the new value if needed
            value = node.get_value(static=False) if node.resolver is not None else node.static_value
            if isinstance(value, Bag):
                value = self._compiler._materialize(value)
            compiled_node.set_value(value, _reason="source")

            # Re-bind pointers on this subtree
            self._binding.unbind_path(path)
            self._binding.bind_subtree(compiled_node, self._data, path)

        elif evt == "upd_attrs":
            # oldvalue is the list of changed attribute names
            if node is not None:
                compiled_node.set_attr(dict(node.attr))
                # Re-bind in case new attrs contain ^pointers
                self._binding.unbind_path(path)
                self._binding.bind_subtree(compiled_node, self._data, path)

        self._rerender()

    def _rerender(self) -> None:
        """Re-render the compiled bag without re-compiling.

        Used after data changes — nodes are already updated by binding.
        """
        self._output = self.render(self.compiled)
