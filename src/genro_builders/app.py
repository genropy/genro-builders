# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BagAppBase — reactive application runtime for genro-builders.

Coordinates the 4-stage pipeline:
    1. Source Bag (recipe with builder, components, ^pointers)
    2. Static Bag (components expanded via _materialize)
    3. Bound Bag (^pointers resolved, subscriptions active)
    4. Output (rendered by compiler)

Reactivity:
    - Recipe change → full rebuild (rebuild())
    - Data change → subscription updates nodes → re-render

Example:
    >>> class MyApp(BagAppBase):
    ...     builder_class = HtmlBuilder
    ...
    ...     def recipe(self, store):
    ...         store.h1(value='^page.title')
    ...         store.p(value='^content.text')
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
        1. __init__: create store, data, binding, compiler
        2. recipe(store): populate the store (override in subclass)
        3. setup(): call recipe + compile + enable auto-compile
        4. Data changes trigger partial re-render automatically
        5. rebuild(): full rebuild on recipe change
    """

    builder_class: type
    compiler_class: type | None = None

    def __init__(self) -> None:
        """Initialize the app. Does NOT call recipe() yet."""
        self._store = BuilderBag(builder=self.builder_class)
        self._data = Bag()
        self._data.set_backref()
        self._binding = BindingManager(on_node_updated=self._on_node_updated)
        self._static_bag: Bag | None = None
        self._auto_compile = False
        self._output: str | None = None

        compiler_cls = self.compiler_class or getattr(self.builder_class, "compiler_class", None)
        if compiler_cls:
            self._compiler: BagCompilerBase | None = compiler_cls(self._store.builder)
        else:
            self._compiler = None

    @property
    def store(self) -> BuilderBag:
        """The source Bag with builder."""
        return self._store

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

        if self._static_bag is not None:
            self._binding.rebind(new_data)
            self._rerender()

    @property
    def compiled(self) -> Bag | None:
        """The compiled Bag (components expanded, pointers resolved)."""
        return self._static_bag

    @property
    def output(self) -> str | None:
        """Last compiled output."""
        return self._output

    def setup(self) -> None:
        """Call recipe() and do initial compile.

        After setup, data changes trigger automatic re-compilation.
        """
        self.recipe(self._store)
        self.compile()
        self._auto_compile = True

    def recipe(self, store: BuilderBag) -> None:
        """Template method: populate the store with builder calls.

        Override in subclass:
            def recipe(self, store):
                store.div(id='main')
                store.p(value='^content.text')
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

        # 1. Compile: materialize components → CompiledBag (pointers not yet resolved)
        self._static_bag = self._compiler.compile(self._store)

        # 2. Make the compiled bag observable for live apps
        if not self._static_bag.backref:
            self._static_bag.set_backref()

        # 3. Bind: resolve pointers + register subscriptions for reactive updates
        self._binding.bind(self._static_bag, self._data)

        # 4. Subscribe to store changes for incremental updates
        if not self._store.backref:
            self._store.set_backref()
        self._store.subscribe(
            "store_watcher",
            delete=self._on_store_deleted,
            insert=self._on_store_inserted,
            update=self._on_store_updated,
        )

        # 5. Render
        self._output = self.render(self._static_bag)
        return self._output

    def rebuild(self) -> str:
        """Full rebuild: clear store, re-run recipe, compile.

        Use when the recipe itself has changed.

        Returns:
            Compiled output string.
        """
        self._binding.unbind()
        self._store.unsubscribe("store_watcher", any=True)
        self._static_bag = None
        self._auto_compile = False

        # Clear and re-populate store
        self._store = BuilderBag(builder=self.builder_class)
        if self._compiler is not None:
            self._compiler.builder = self._store.builder

        self.recipe(self._store)
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

        Triggers re-render of the static bag.
        """
        if self._auto_compile:
            self._rerender()

    def _on_store_deleted(
        self,
        node: BagNode | None = None,
        pathlist: list | None = None,
        ind: int | None = None,
        evt: str = "",
        **kwargs: Any,
    ) -> None:
        """Called when a node is deleted from the store.

        Removes the corresponding node from the compiled bag,
        cleans up bindings, and re-renders.
        """
        if not self._auto_compile or self._static_bag is None or node is None:
            return
        parts = [str(p) for p in pathlist] if pathlist else []
        parts.append(node.label)
        path = ".".join(parts)
        self._binding.unbind_path(path)
        self._static_bag.del_item(path, _reason="store")
        self._rerender()

    def _on_store_inserted(
        self,
        node: BagNode | None = None,
        pathlist: list | None = None,
        ind: int | None = None,
        evt: str = "",
        **kwargs: Any,
    ) -> None:
        """Called when a node is inserted into the store.

        Materializes the new node, inserts it into the compiled bag
        at the same position, binds ^pointers, and re-renders.
        """
        if not self._auto_compile or self._static_bag is None or node is None:
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
            target_bag = self._static_bag.get_item(parent_path)
            if not isinstance(target_bag, Bag):
                return
        else:
            target_bag = self._static_bag

        # Insert the materialized node at the same position
        new_node = target_bag.set_item(
            node.label,
            value,
            _attributes=dict(node.attr),
            node_position=ind,
            _reason="store",
            node_tag=node.node_tag,
        )

        # Bind ^pointers on the new subtree
        node_path = f"{parent_path}.{node.label}" if parent_path else node.label
        self._binding.bind_subtree(new_node, self._data, node_path)

        self._rerender()

    def _on_store_updated(
        self,
        node: BagNode | None = None,
        pathlist: list | None = None,
        oldvalue: Any = None,
        evt: str = "",
        **kwargs: Any,
    ) -> None:
        """Called when a node in the store is updated (value or attributes).

        Updates the corresponding node in the compiled bag,
        re-binds ^pointers if needed, and re-renders.
        """
        if not self._auto_compile or self._static_bag is None or pathlist is None:
            return
        if self._compiler is None:
            return

        path = ".".join(str(p) for p in pathlist)
        compiled_node = self._static_bag.get_node(path)
        if compiled_node is None:
            return

        if evt == "upd_value":
            # Materialize the new value if needed
            value = node.get_value(static=False) if node.resolver is not None else node.static_value
            if isinstance(value, Bag):
                value = self._compiler._materialize(value)
            compiled_node.set_value(value, _reason="store")

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
        """Re-render the static bag without re-compiling.

        Used after data changes — nodes are already updated by binding.
        """
        if self._static_bag is not None:
            self._output = self.render(self._static_bag)
