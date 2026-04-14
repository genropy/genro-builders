# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""ReactivityEngine — encapsulated reactive layer for builders.

Manages subscribe, incremental compile (source change handlers),
and output suspension. Created lazily by ``builder.subscribe()`` —
a builder without subscribe never instantiates this engine.

Reactivity follows the legacy pattern: the BindingManager notifies
all built nodes whose ^pointers are affected by a data change.
Each node decides what to do (execute func, update widget, etc.).
Cascade propagation is natural — no guard, no topological sort.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from genro_bag import Bag

from ._binding import BindingManager

if TYPE_CHECKING:
    from genro_bag import BagNode



class ReactivityEngine:
    """Encapsulated reactive layer for a builder.

    Holds binding manager, timers, and output state.
    Calls back into the builder for build walk and render operations.
    """

    def __init__(self, builder: Any) -> None:
        self._builder = builder
        self._binding = BindingManager(
            on_node_updated=self._on_node_updated,
        )
        self._auto_compile = False
        self._output_suspended = False
        self._output_pending = False
        self._output: str | None = None

    @property
    def output(self) -> str | None:
        """Last rendered output string, or None before first render."""
        return self._output

    @property
    def binding(self) -> BindingManager:
        """The binding manager instance."""
        return self._binding

    # -----------------------------------------------------------------------
    # Lifecycle
    # -----------------------------------------------------------------------

    def subscribe(self) -> None:
        """Activate reactive bindings on the built Bag.

        The BindingManager collects all built nodes with ^pointers.
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
        self._rerender()

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
            self._rerender()

    # -----------------------------------------------------------------------
    # Output management
    # -----------------------------------------------------------------------

    def _on_node_updated(self, node: BagNode) -> None:
        """Called by BindingManager when a reactive node is affected.

        The node has its turn — it decides what to do. If it has a func
        attribute, it executes and writes to the data store (cascade).
        The rerender happens regardless.
        """
        if self._auto_compile:
            self._rerender()

    def _rerender(self) -> None:
        """Re-render the built bag without re-building."""
        if self._output_suspended:
            self._output_pending = True
            return
        b = self._builder
        self._output = b.render(b.built)

    def suspend_output(self) -> None:
        """Suspend render/compile output."""
        self._output_suspended = True

    def resume_output(self) -> None:
        """Resume render/compile output. Flushes pending if any."""
        self._output_suspended = False
        if self._output_pending:
            self._output_pending = False
            self._rerender()

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
        # Stop timers and unregister before deleting
        built_node = b.built.get_node(path)
        if built_node is not None:
            if hasattr(built_node, "stop_interval"):
                built_node.stop_interval()
            self._binding.unregister_node(built_node)
        b.built.del_item(path, _reason="source")
        self._rerender()

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
            self._rerender()
            return None

        if node.attr.get("_is_data_element"):
            b._prepare_data_element(node)

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
                self._rerender()

            return cont_inserted()

        b._materialize_inserted(node, value, target_bag, node_path, ind)
        built_node = target_bag.get_node(node.label)
        if built_node is not None:
            self._binding.register_node(built_node)
        self._rerender()
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
            self._rerender()
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
                    self._rerender()

                return cont_updated()

            b._materialize_updated(built_node, value, path)

        elif evt == "upd_attrs":
            if node is not None:
                built_node.set_attr(dict(node.attr))

        self._rerender()
