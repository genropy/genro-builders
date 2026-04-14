# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BuiltBag and BuiltBagNode — execution-focused Bag for the built tree.

The built Bag is the output of the build phase. It is completely
self-sufficient: renderer, compiler, and reactive dispatch consume
it without any reference to source, grammar, or builder.

BuiltBagNode provides:
    - data — direct reference to the data Bag (set at build time)
    - runtime_value / runtime_attrs — resolved attributes for render/compile
    - execute_func() — execute a data provider function (formula/controller)
    - set_data() — write to data Bag with anti-loop protection

BuiltBag provides:
    - Uses BuiltBagNode as node class
    - Pure container, no builder/grammar knowledge
"""
from __future__ import annotations

import inspect
from typing import Any

from genro_bag import Bag, BagNode
from genro_toolbox.smarttimer import cancel_timer, set_interval, set_timeout

from .builder._binding import is_pointer


def _make_timer_callback(
    built_bag: Bag, node_path: str, timer_id_holder: list,
) -> Any:
    """Create a timer callback that looks up the node by path.

    If the node no longer exists in the built bag, auto-cancels
    the timer. No reference to the node object — no memory leak.

    Args:
        built_bag: The root built Bag (long-lived object).
        node_path: Path to the node in the built bag.
        timer_id_holder: Single-element list holding the timer_id
            (set after timer creation, needed for auto-cancel).
    """
    def callback():
        node = built_bag.get_node(node_path)
        if node is None:
            if timer_id_holder:
                cancel_timer(timer_id_holder[0])
            return
        node._execute_now()
    return callback


class BuiltBagNode(BagNode):
    """Node in the built tree. Resolves pointers, executes functions, writes data.

    Each node holds a direct reference to the data Bag (_data),
    set during materialization. No parent chain traversal needed.

    Inherits from BagNode (not BuilderBagNode): no grammar delegation,
    no schema awareness, no __getattr__ magic. Pure execution.
    """

    _data: Bag | None = None
    _delay_timer: str | None = None
    _interval_timer: str | None = None

    def _root_bag(self) -> Bag:
        """Walk up parent chain to find the root built Bag."""
        bag = self._parent_bag
        while bag is not None:
            parent_node = bag.parent_node
            if parent_node is None:
                return bag
            bag = parent_node._parent_bag
        return self._parent_bag

    @property
    def data(self) -> Bag:
        """Direct access to the data Bag — O(1)."""
        if self._data is not None:
            return self._data
        return Bag()

    def _resolve_datapath(self) -> str:
        """Compose hierarchical datapath by walking up the ancestor chain.

        Collects ``datapath`` attributes from ancestor nodes. Relative
        datapaths (starting with '.') are concatenated; absolute datapaths
        reset the chain.
        """
        parts: list[str] = []
        current_bag = self._parent_bag

        while current_bag is not None:
            node = current_bag.parent_node
            if node is None:
                break
            dp = node.attr.get("datapath", "")
            if dp:
                parts.append(dp)
                if not dp.startswith("."):
                    break
            current_bag = node._parent_bag

        parts.reverse()

        result = ""
        for part in parts:
            if part.startswith("."):
                result = f"{result}.{part[1:]}" if result else part[1:]
            else:
                result = part
        return result

    def abs_datapath(self, path: str) -> str:
        """Resolve any path form to an absolute datapath.

        Supports:
            'user.name'  — absolute: returned as-is
            '.name'      — relative: resolved from this node's datapath
        """
        if path.startswith("."):
            datapath = self._resolve_datapath()
            if not datapath:
                return path[1:] if path[1:] else ""
            return f"{datapath}.{path[1:]}" if path[1:] else datapath
        return path

    def get_relative_data(self, path: str) -> Any:
        """Read a value from the data Bag, resolving relative paths.

        Args:
            path: Data path. Syntax:
                'alfa.beta'       — absolute
                '.beta'           — relative to this node's datapath
                'alfa.beta?color' — attribute 'color' of node 'alfa.beta'
        """
        attr_name = None
        if "?" in path:
            path, attr_name = path.split("?", 1)
        resolved = self.abs_datapath(path)
        if attr_name is not None:
            node = self.data.get_node(resolved)
            return node.attr.get(attr_name) if node is not None else None
        return self.data.get_item(resolved)

    def set_relative_data(self, path: str, value: Any) -> None:
        """Write a value to the data Bag, resolving relative paths.

        Anti-loop: _reason=self is automatic.

        Args:
            path: Data path (same syntax as get_relative_data).
            value: The value to set.
        """
        attr_name = None
        if "?" in path:
            path, attr_name = path.split("?", 1)
        resolved = self.abs_datapath(path)
        if attr_name is not None:
            self.data.set_attr(resolved, **{attr_name: value})
        else:
            self.data.set_item(resolved, value, _reason=self)

    def current_from_datasource(self, value: Any) -> Any:
        """Resolve a single value: if ^pointer, read from data; else return as-is."""
        if is_pointer(value):
            return self.get_relative_data(value[1:])
        return value

    def evaluate_on_node(self) -> dict[str, Any]:
        """Resolve all attributes and value in two passes.

        Pass 1: resolve ^pointer strings to values, skip callables.
        Pass 2: call each callable passing resolved attrs as kwargs.

        Returns dict with node_value, attrs, node.
        """
        raw_value = self.get_value(static=True)
        resolved_value = self.current_from_datasource(raw_value)

        # Pass 1: resolve non-callable attributes
        resolved: dict[str, Any] = {}
        callables: dict[str, Any] = {}
        for k, v in self.attr.items():
            if callable(v) and not isinstance(v, Bag):
                callables[k] = v
            else:
                resolved[k] = self.current_from_datasource(v)

        # Pass 2: execute callables with resolved attrs as context
        for k, func in callables.items():
            sig = inspect.signature(func)
            has_var_keyword = any(
                p.kind == inspect.Parameter.VAR_KEYWORD
                for p in sig.parameters.values()
            )
            if has_var_keyword:
                kwargs = {p: resolved[p] for p in resolved if not p.startswith("_")}
            else:
                kwargs: dict[str, Any] = {}
                for pname, param in sig.parameters.items():
                    if pname in resolved:
                        kwargs[pname] = resolved[pname]
                    elif param.default is not inspect.Parameter.empty:
                        kwargs[pname] = self.current_from_datasource(
                            param.default,
                        )
            resolved[k] = func(**kwargs)

        return {
            "node_value": resolved_value,
            "attrs": resolved,
            "node": self,
        }

    @property
    def runtime_value(self) -> Any:
        """Node value with ^pointers resolved and callables executed."""
        return self.evaluate_on_node()["node_value"]

    @property
    def runtime_attrs(self) -> dict[str, Any]:
        """Attributes with ^pointers resolved, callables executed, datapath excluded."""
        attrs = self.evaluate_on_node()["attrs"]
        attrs.pop("datapath", None)
        return attrs

    def execute_func(self, raw_attrs: dict[str, Any]) -> Any:
        """Execute this node's data provider function.

        Resolves ^pointers via get_relative_data, executes func.
        """
        resolved = {
            k: self.current_from_datasource(v)
            for k, v in raw_attrs.items()
            if not k.startswith("_")
        }
        func = resolved.pop("func")
        if self.attr.get("_accepts_node"):
            resolved["_node"] = self
        return func(**resolved)

    def on_data_changed(self, changed_path: str, reason: Any = None) -> None:
        """Called by BindingManager when a dependent data path changes.

        The node has its turn — it decides what to do.
        If it has a func (data_formula/data_controller), executes it
        and writes the result to the data store (cascade propagation).

        If _delay is set, debounces: cancels previous timer, schedules
        new execution after _delay ms. Only the last trigger executes.
        """
        func = self.attr.get("func")
        if func is None:
            return

        delay = self.attr.get("_delay")
        if delay is not None:
            if self._delay_timer is not None:
                cancel_timer(self._delay_timer)
            holder: list[str] = []
            self._delay_timer = set_timeout(
                delay, _make_timer_callback(self._root_bag(), self.fullpath, holder),
            )
            holder.append(self._delay_timer)
        else:
            self._execute_now()

    def _execute_now(self) -> None:
        """Execute this node's func and write result to data store."""
        self._delay_timer = None
        raw_attrs = {k: v for k, v in self.attr.items() if not k.startswith("_")}
        result = self.execute_func(raw_attrs)

        path = self.attr.get("_data_path")
        if path is not None and result is not None:
            if isinstance(result, dict):
                result = Bag(source=result)
            self.set_relative_data(path, result)

    def start_interval(self) -> None:
        """Start periodic execution if _interval is set."""
        interval = self.attr.get("_interval")
        if interval is not None:
            holder: list[str] = []
            self._interval_timer = set_interval(
                interval, _make_timer_callback(self._root_bag(), self.fullpath, holder),
            )
            holder.append(self._interval_timer)

    def stop_interval(self) -> None:
        """Stop periodic execution."""
        if self._interval_timer is not None:
            cancel_timer(self._interval_timer)
            self._interval_timer = None
        if self._delay_timer is not None:
            cancel_timer(self._delay_timer)
            self._delay_timer = None


class BuiltBag(Bag):
    """Bag for the built tree. Pure container, no builder/grammar knowledge."""

    node_class: type[BagNode] = BuiltBagNode
