# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Reactivity mixin: formula/controller execution, output suspension.

Handles topological sorting of formulas, data-change propagation,
debounce (_delay) and periodic (_interval) timers, and output
suspend/resume for batched rendering.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from genro_bag import Bag
from genro_toolbox.smarttimer import cancel_timer, set_timeout

from ..pointer import is_pointer

if TYPE_CHECKING:
    from genro_bag import BagNode


class _ReactivityMixin:
    """Mixin for formula/controller reactivity and output management."""

    # -----------------------------------------------------------------------
    # Output suspension
    # -----------------------------------------------------------------------

    def _rebind_data(self, new_data: Bag) -> None:
        """Rebind this builder to new data. Called by BuilderManager."""
        if self._auto_compile:
            self._binding.rebind(new_data)
            self._rerender()

    def _on_node_updated(self, node: BagNode) -> None:
        """Called by BindingManager when a bound node is updated."""
        if self._auto_compile:
            self._rerender()

    def _rerender(self) -> None:
        """Re-render the built bag without re-building.

        If output is suspended, marks as pending and returns.
        The actual render happens on resume_output().
        """
        if self._output_suspended:
            self._output_pending = True
            return
        self._output = self.render(self.built)

    def suspend_output(self) -> None:
        """Suspend render/compile output.

        While suspended, data changes and formula re-executions still
        happen normally, but no render/compile is triggered.
        Call resume_output() to flush a single render.
        """
        self._output_suspended = True

    def resume_output(self) -> None:
        """Resume render/compile output.

        If any render was pending during suspension, triggers one now.
        """
        self._output_suspended = False
        if self._output_pending:
            self._output_pending = False
            self._rerender()

    # -----------------------------------------------------------------------
    # Formula/controller reactivity
    # -----------------------------------------------------------------------

    def _topological_sort_formulas(self) -> list[str]:
        """Sort formula entries by dependency order. Detect cycles.

        Builds a DAG from formula dependencies: if formula A writes to
        path X, and formula B has ^X in its kwargs, then A must execute
        before B.

        Returns:
            List of entry_ids in execution order (dependencies first).

        Raises:
            ValueError: If a circular dependency is detected.
        """
        if not self._formula_registry:
            return []

        # Build: path -> entry_id (which formula writes to which path)
        path_to_entry: dict[str, str] = {}
        for entry_id, entry in self._formula_registry.items():
            if entry["path"] is not None:
                path_to_entry[entry["path"]] = entry_id

        # Build adjacency: entry_id -> set of entry_ids it depends on
        deps: dict[str, set[str]] = {eid: set() for eid in self._formula_registry}
        for entry_id, entry in self._formula_registry.items():
            for v in entry["raw_attrs"].values():
                if is_pointer(v):
                    dep_path = self._resolve_pointer_path(v, entry["node"])
                    dep_entry = path_to_entry.get(dep_path)
                    if dep_entry is not None and dep_entry != entry_id:
                        deps[entry_id].add(dep_entry)

        # Topological sort (Kahn's algorithm)
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

    def _on_formula_data_changed(
        self,
        node: BagNode | None = None,
        pathlist: list | None = None,
        oldvalue: Any = None,
        evt: str = "",
        **kwargs: Any,
    ) -> None:
        """Re-execute formula/controller when their dependencies change.

        Uses _formula_order (topological sort) to ensure dependent formulas
        execute after their dependencies. Cascades: if formula A writes to
        a path that formula B depends on, B re-executes after A.

        Entries with _delay use set_timeout for debounce.
        """
        if pathlist is None or not self._formula_registry:
            return

        changed_path = ".".join(str(p) for p in pathlist)
        changed_paths = {changed_path}
        rerun_needed = False

        for entry_id in self._formula_order:
            entry = self._formula_registry[entry_id]
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
                            self._reexecute_formula(entry)
                        rerun_needed = True
                        if entry["path"] is not None:
                            changed_paths.add(entry["path"])
                        break

        if rerun_needed:
            self._rerender()

    def _schedule_delayed_formula(
        self, entry_id: str, entry: dict[str, Any], delay: float,
    ) -> None:
        """Schedule a delayed formula re-execution (debounce).

        Cancels any pending timer for the same entry, then schedules
        a new one. Only the last trigger within the delay window executes.
        """
        old_timer = self._active_timers.get(entry_id)
        if old_timer is not None:
            cancel_timer(old_timer)

        def on_timeout() -> None:
            self._active_timers.pop(entry_id, None)
            self._reexecute_formula(entry)
            self._rerender()

        timer_id = set_timeout(delay, on_timeout)
        self._active_timers[entry_id] = timer_id

    def _on_interval_tick(self, entry_id: str) -> None:
        """Periodic re-execution of a formula/controller with _interval."""
        entry = self._formula_registry.get(entry_id)
        if entry is not None:
            self._reexecute_formula(entry)
            self._rerender()

    def _resolve_pointer_path(self, raw: str, node: BagNode) -> str:
        """Extract absolute data path from a ^pointer string."""
        path = raw[1:]  # strip ^
        if "?" in path:
            path = path.split("?", 1)[0]
        return node.abs_datapath(path)

    def _reexecute_formula(self, entry: dict[str, Any]) -> None:
        """Re-execute a single formula/controller with fresh data."""
        node = entry["node"]
        path = entry["path"]
        raw_attrs = entry["raw_attrs"]
        tag = entry["tag"]

        resolved = self._resolve_infra_kwargs(raw_attrs, node, self.data)

        if tag == "data_formula":
            func = resolved.pop("func", None)
            if func is not None and path is not None:
                result = self._call_with_node(func, node, resolved)
                if isinstance(result, dict):
                    result = Bag(source=result)
                self.data.set_item(path, result)
        elif tag == "data_controller":
            func = resolved.pop("func", None)
            if func is not None:
                self._call_with_node(func, node, resolved)
