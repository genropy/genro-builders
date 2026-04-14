# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""ReactivityEngine — encapsulated reactive layer for builders.

Manages subscribe, formula re-execution, debounce/interval timers,
incremental compile (source change handlers), and output suspension.
Created lazily by ``builder.subscribe()`` — a builder without subscribe
never instantiates this engine.

The engine holds its own state (binding, formula registry, timers) and
calls back into the builder for build operations (_build_walk,
_register_bindings, render, etc.).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from genro_bag import Bag
from genro_toolbox.smarttimer import cancel_timer, set_interval, set_timeout

from ._binding import BindingManager, is_pointer

if TYPE_CHECKING:
    from genro_bag import BagNode



class ReactivityEngine:
    """Encapsulated reactive layer for a builder.

    Holds binding manager, formula registry, timers, and output state.
    Calls back into the builder for build walk and render operations.
    """

    def __init__(self, builder: Any) -> None:
        self._builder = builder
        self._binding = BindingManager(
            on_node_updated=self._on_node_updated,
            on_formulas_triggered=self._dispatch_formulas,
        )
        self._formula_registry: dict[str, dict[str, Any]] = {}
        self._formula_order: list[str] = []
        self._active_timers: dict[str, str] = {}
        self._auto_compile = False
        self._output_suspended = False
        self._output_pending = False
        self._output: str | None = None
        self._dispatching_formulas = False

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

        Enables formula re-execution on data changes, ``_delay``
        debounce, ``_interval`` periodic execution, and
        source change handlers (incremental compile).
        """
        b = self._builder
        self._binding.subscribe(b.built, b.data)

        b.source.subscribe(
            "source_watcher",
            delete=self._on_source_deleted,
            insert=self._on_source_inserted,
            update=self._on_source_updated,
        )

        for entry_id, entry in self._formula_registry.items():
            interval = entry.get("_interval")
            if interval is not None:
                timer_id = set_interval(
                    interval,
                    self._on_interval_tick,
                    entry_id,
                )
                self._active_timers[f"interval:{entry_id}"] = timer_id

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
        """Clear binding, timers, formula registry."""
        self._binding.unbind()
        for timer_id in self._active_timers.values():
            cancel_timer(timer_id)
        self._active_timers = {}
        self._formula_registry = {}

    # -----------------------------------------------------------------------
    # Data rebind
    # -----------------------------------------------------------------------

    def rebind_data(self, new_data: Bag) -> None:
        """Rebind this engine to new data. Called by BuilderManager."""
        if self._auto_compile:
            self._binding.rebind(new_data)
            self._rerender()

    # -----------------------------------------------------------------------
    # Output management
    # -----------------------------------------------------------------------

    def _on_node_updated(self, node: BagNode) -> None:
        """Called by BindingManager when a bound node is updated."""
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
    # Formula/controller reactivity
    # -----------------------------------------------------------------------

    def _topological_sort_formulas(self) -> list[str]:
        """Sort formula entries by dependency order. Detect cycles."""
        if not self._formula_registry:
            return []

        path_to_entry: dict[str, str] = {}
        for entry_id, entry in self._formula_registry.items():
            if entry["path"] is not None:
                path_to_entry[entry["path"]] = entry_id

        deps: dict[str, set[str]] = {eid: set() for eid in self._formula_registry}
        for entry_id, entry in self._formula_registry.items():
            for v in entry["raw_attrs"].values():
                if is_pointer(v):
                    dep_path = self._resolve_pointer_path(v, entry["node"])
                    dep_entry = path_to_entry.get(dep_path)
                    if dep_entry is not None and dep_entry != entry_id:
                        deps[entry_id].add(dep_entry)

        visited: set[str] = set()
        in_stack: set[str] = set()
        order: list[str] = []

        def visit(eid: str) -> None:
            if eid in in_stack:
                cycle_path = self._formula_registry[eid].get("path", eid)
                raise ValueError(
                    f"Circular dependency in data_formula: {cycle_path}"
                )
            if eid in visited:
                return
            in_stack.add(eid)
            for dep_eid in deps.get(eid, ()):
                visit(dep_eid)
            in_stack.discard(eid)
            visited.add(eid)
            order.append(eid)

        for eid in self._formula_registry:
            visit(eid)

        return order

    def _dispatch_formulas(
        self, changed_paths: set[str], reason: Any,
    ) -> None:
        """Re-execute formulas/controllers whose dependencies match.

        Called by BindingManager as part of unified dispatch.
        Processes formulas in topological order, cascading output paths.
        The ``_dispatching_formulas`` guard prevents re-entry when a
        formula writes to data and triggers a nested ``_on_data_changed``.
        """
        if not self._formula_registry or self._dispatching_formulas:
            return

        self._dispatching_formulas = True
        try:
            changed_paths = set(changed_paths)
            rerun_needed = False

            for entry_id in self._formula_order:
                entry = self._formula_registry[entry_id]
                if entry["node"] is reason:
                    continue
                for v in entry["raw_attrs"].values():
                    if is_pointer(v):
                        dep_path = self._resolve_pointer_path(v, entry["node"])
                        if any(
                            dep_path == cp
                            or cp.startswith(dep_path + ".")
                            or dep_path.startswith(cp + ".")
                            for cp in changed_paths
                        ):
                            delay = entry.get("_delay")
                            if delay is not None:
                                self._schedule_delayed_formula(entry_id, entry, delay)
                            else:
                                self._execute_data_provider(entry)
                            rerun_needed = True
                            if entry["path"] is not None:
                                changed_paths.add(entry["path"])
                            break

            if rerun_needed:
                self._rerender()
        finally:
            self._dispatching_formulas = False

    def _schedule_delayed_formula(
        self, entry_id: str, entry: dict[str, Any], delay: float,
    ) -> None:
        """Schedule a delayed formula re-execution (debounce)."""
        old_timer = self._active_timers.get(entry_id)
        if old_timer is not None:
            cancel_timer(old_timer)

        def on_timeout() -> None:
            self._active_timers.pop(entry_id, None)
            self._execute_data_provider(entry)
            self._rerender()

        timer_id = set_timeout(delay, on_timeout)
        self._active_timers[entry_id] = timer_id

    def _on_interval_tick(self, entry_id: str) -> None:
        """Periodic re-execution of a formula/controller with _interval."""
        entry = self._formula_registry.get(entry_id)
        if entry is not None:
            self._execute_data_provider(entry)
            self._rerender()

    def _resolve_pointer_path(self, raw: str, node: BagNode) -> str:
        """Extract absolute data path from a ^pointer string."""
        path = raw[1:]  # strip ^
        if "?" in path:
            path = path.split("?", 1)[0]
        return node.abs_datapath(path)

    def _execute_data_provider(self, entry: dict[str, Any]) -> None:
        """Re-execute a single formula/controller with fresh data."""
        b = self._builder
        node = entry["node"]
        resolved = b._resolve_infra_kwargs(entry["raw_attrs"], node, b.data)
        result = b._call_with_node(resolved.pop("func"), node, resolved)
        if entry["tag"] == "data_formula":
            if isinstance(result, dict):
                result = Bag(source=result)
            b.data.set_item(entry["path"], result, _reason=node)

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
        if node.attr.get("_is_data_element"):
            return
        b = self._builder
        parts = [str(p) for p in pathlist] if pathlist else []
        parts.append(node.label)
        path = ".".join(parts)
        self._binding.unbind_path(path)
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

        if node.attr.get("_is_data_element"):
            b._process_infra_node(node, b.data)
            self._rerender()
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
                self._rerender()

            return cont_inserted()

        b._materialize_inserted(node, value, target_bag, node_path, ind)
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

        if node is not None and node.attr.get("_is_data_element"):
            b._process_infra_node(node, b.data)
            self._rerender()
            return None

        path = ".".join(str(p) for p in pathlist)
        built_node = b.built.get_node(path)
        if built_node is None:
            return None

        if evt == "upd_value":
            value = node.get_value(static=False) if node.resolver is not None else node.static_value

            self._binding.unbind_path(path)

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
                self._binding.unbind_path(path)
                b._register_bindings(
                    built_node, path, b.data, self._binding,
                )

        self._rerender()
