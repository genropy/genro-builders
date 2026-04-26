# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""FormulaResolver — pull-based computed data values.

Installed on data store nodes by ``data_formula`` during build.
Dependencies are kept as ``^pointer`` strings in the resolver kwargs.
They are resolved **at load time** via the built context node's
``abs_datapath``. This keeps the build tree free of absolute paths:
resolution is a render/compile-time concern.

Modes:
    cache_time=0 (default): read_only=True, every read recomputes.
    cache_time=N (N>0): passive cache, TTL of N seconds. read_only=False.
    interval=N (N>0): active cache, background refresh every N seconds.
        read_only=False — result stored in node._value, triggers
        data change events. Requires async context.
"""

from __future__ import annotations

from typing import Any

from genro_bag import Bag
from genro_bag.resolver import BagSyncResolver


def _is_pointer(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("^")


class FormulaResolver(BagSyncResolver):
    """Resolver for computed data values (pull-based data_formula).

    Pointers in kwargs (values starting with ``^``) are resolved at
    each load through the built context node's ``abs_datapath``. Non
    pointer kwargs are passed through as-is to ``func``.
    """

    class_kwargs: dict[str, Any] = {
        "cache_time": 0,
        "interval": None,
        "read_only": True,
        "func": None,
    }
    class_args: list[str] = []
    internal_params: set[str] = {
        "cache_time", "interval", "read_only", "retry_policy", "as_bag", "func",
    }

    def init(self) -> None:
        """Post-init hook: set up built context + data bag."""
        self._data_bag: Bag | None = None
        self._built_context: Any = None

    def on_loading(self, kw: dict[str, Any]) -> dict[str, Any]:
        """Resolve pointer kwargs against the built context + data bag.

        Non-pointer kwargs pass through unchanged. Pointers are resolved
        via ``built_context.abs_datapath(path)`` into absolute data-store
        paths and read from ``data_bag``.
        """
        ctx = self._built_context
        data_bag = self._data_bag
        if ctx is None or data_bag is None:
            return kw

        resolved: dict[str, Any] = {}
        for name, value in kw.items():
            if name in self.internal_params:
                resolved[name] = value
                continue
            if _is_pointer(value):
                abs_path = ctx.abs_datapath(value[1:])
                resolved[name] = data_bag.get_item(abs_path)
            else:
                resolved[name] = value
        return resolved

    def load(self) -> Any:
        """Compute the formula value by calling func with resolved kwargs."""
        kw = self.kw
        func = kw["func"]
        call_kwargs = {
            name: value
            for name, value in kw.items()
            if name not in self.internal_params
        }
        result = func(**call_kwargs)
        if isinstance(result, dict):
            result = Bag(source=result)
        return result

    def _background_load(self) -> None:
        """Background refresh: recompute and notify data subscribers."""
        from datetime import datetime

        result = self.load()
        if isinstance(result, dict):
            result = Bag(source=result)
        self._cache_last_update = datetime.now()
        node = self._parent_node
        if node is not None:
            node.set_value(result)
        else:
            self._cached_value = result
