# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""ReactivityEngine — encapsulated reactive layer for builders.

Pull model: data changes set a dirty flag and the builder re-renders
on demand. No per-node dispatch, no output caching in the builder.

Manages:
- BindingManager subscription (data change → dirty signal)
- Source change handlers (incremental compile)

Created lazily by ``builder.subscribe()`` — a builder without
subscribe never instantiates this engine.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from genro_bag import Bag

from ._binding import BindingManager

if TYPE_CHECKING:
    from genro_bag import BagNode


class ReactivityEngine:
    """Encapsulated reactive layer for a builder.

    Holds binding manager and incremental compile handlers.
    Signals dirty to the builder/manager when data or source changes.
    """

    def __init__(self, builder: Any) -> None:
        self._builder = builder
        self._binding = BindingManager(
            on_data_changed=self._on_data_changed,
        )
        self._auto_compile = False

    @property
    def binding(self) -> BindingManager:
        """The binding manager instance."""
        return self._binding

    # -----------------------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------------------

    def subscribe(self) -> None:
        """Activate reactive bindings on the built Bag.

        The BindingManager subscribes to data changes.
        Source change handlers enable incremental compile.
        """
        b = self._builder
        self._binding.subscribe(b.built, b.data)

        b.source.subscribe(
            "source_watcher",
            delete=self._on_source_deleted,
            insert=self._on_source_inserted,
            update=self._on_source_updated,
        )

        self._auto_compile = True

    def rebuild(self, main: Any = None) -> None:
        """Full rebuild: clear source, optionally re-populate, build."""
        b = self._builder
        b.source.unsubscribe("source_watcher", any=True)
        self._auto_compile = False
        b._clear_source()
        if main is not None:
            main(b.source)
        b.build()

    def clear(self) -> None:
        """Clear binding."""
        self._binding.unbind()

    # -----------------------------------------------------------------------
    # Data rebind
    # -----------------------------------------------------------------------

    def rebind_data(self, new_data: Bag) -> None:
        """Rebind this engine to new data. Called by BuilderManager."""
        if self._auto_compile:
            self._binding.subscribe(self._builder.built, new_data)

    # -----------------------------------------------------------------------
    # Callbacks
    # -----------------------------------------------------------------------

    def _on_data_changed(self, changed_path: str) -> None:
        """Called by BindingManager on any data change."""

    # -----------------------------------------------------------------------
    # Source change handlers (incremental compile)
    # -----------------------------------------------------------------------

    def _on_source_deleted(
        self,
        node: BagNode | None = None,
        pathlist: list | None = None,
        ind: int | None = None,
        evt: str = "",
        **kwargs: Any,
    ) -> None:
        """Called when a node is deleted from the source."""
        if not self._auto_compile or node is None:
            return
        b = self._builder
        parts = [str(p) for p in pathlist] if pathlist else []
        parts.append(node.label)
        path = ".".join(parts)
        built_node = b.built.get_node(path)
        if built_node is not None:
            self._binding.unregister_node(built_node)
        b.built.del_item(path, _reason="source")

    def _on_source_inserted(
        self,
        node: BagNode | None = None,
        pathlist: list | None = None,
        ind: int | None = None,
        evt: str = "",
        **kwargs: Any,
    ) -> Any:
        """Called when a node is inserted into the source."""
        if not self._auto_compile or node is None:
            return None

        b = self._builder

        if node.node_tag == "data_setter":
            b._execute_data_setter(node, b.data)
            return None

        if node.node_tag == "data_formula":
            b._install_formula_resolver(node, b.data)
            return None

        parent_path = ".".join(str(p) for p in pathlist) if pathlist else ""

        if parent_path:
            target_bag = b.built.get_item(parent_path)
            if not isinstance(target_bag, Bag):
                return None
        else:
            target_bag = b.built

        node_path = f"{parent_path}.{node.label}" if parent_path else node.label

        value = node.get_value(static=False) if node.resolver is not None else node.static_value

        if b._is_coroutine(value):
            async def cont_inserted(value=value):
                resolved = await value
                b._materialize_inserted(
                    node, resolved, target_bag, node_path, ind,
                )
                self._binding.register_node(target_bag.get_node(node.label))

            return cont_inserted()

        b._materialize_inserted(node, value, target_bag, node_path, ind)
        built_node = target_bag.get_node(node.label)
        if built_node is not None:
            self._binding.register_node(built_node)
        return None

    def _on_source_updated(
        self,
        node: BagNode | None = None,
        pathlist: list | None = None,
        oldvalue: Any = None,
        evt: str = "",
        **kwargs: Any,
    ) -> Any:
        """Called when a node in the source is updated."""
        if not self._auto_compile or pathlist is None:
            return None

        b = self._builder

        if node is not None and node.node_tag == "data_setter":
            b._execute_data_setter(node, b.data)
            return None

        if node is not None and node.node_tag == "data_formula":
            b._install_formula_resolver(node, b.data)
            return None

        if node is not None and node.attr.get("_is_data_element"):
            b._prepare_data_element(node)

        path = ".".join(str(p) for p in pathlist)
        built_node = b.built.get_node(path)
        if built_node is None:
            return None

        if evt == "upd_value":
            value = node.get_value(static=False) if node.resolver is not None else node.static_value

            if b._is_coroutine(value):
                async def cont_updated(value=value):
                    resolved = await value
                    b._materialize_updated(built_node, resolved, path)

                return cont_updated()

            b._materialize_updated(built_node, value, path)

        elif evt == "upd_attrs":
            if node is not None:
                built_node.set_attr(dict(node.attr))

        return None
