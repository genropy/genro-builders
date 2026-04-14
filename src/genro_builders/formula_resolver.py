# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""FormulaResolver — pull-based computed data values.

Installed on data store nodes by ``data_formula`` during build.
Computes value on-demand: when ``data['area']`` is read, the resolver
calls ``func(base=data['base'], altezza=data['altezza'])`` and returns
the result. No push, no cascade, no built-bag node.

Cache modes:
    cache_time=0 (default): read_only=True, every read recomputes.
    cache_time=-N: active cache, background refresh every N seconds.
        read_only=False — result stored in node._value, triggers
        data change events. Requires async context.
    cache_time=N (N>0): passive cache, TTL of N seconds.
        read_only=False — cached, recomputes on expiry.
"""

from __future__ import annotations

from typing import Any

from genro_bag import Bag
from genro_bag.resolver import BagSyncResolver


class FormulaResolver(BagSyncResolver):
    """Resolver for computed data values (pull-based data_formula).

    Installed on data store nodes at build time. Reads dependencies
    from the same data Bag and calls func to produce the value.

    With cache_time=0 (default): pure pull, every read recomputes.
    With cache_time<0: active cache with periodic background refresh.
    """

    class_kwargs: dict[str, Any] = {
        "cache_time": 0,
        "read_only": True,
        "func": None,
    }
    class_args: list[str] = []
    internal_params: set[str] = {
        "cache_time", "read_only", "retry_policy", "as_bag", "func",
    }

    def init(self) -> None:
        """Post-init hook: set up dependency tracking."""
        self._data_bag: Bag | None = None
        self._dep_paths: dict[str, str] = {}
        self._static_kwargs: dict[str, Any] = {}

    def load(self) -> Any:
        """Compute the formula value by resolving dependencies."""
        func = self._kw["func"]
        data_bag = self._data_bag
        resolved = dict(self._static_kwargs)
        if data_bag is not None:
            for name, path in self._dep_paths.items():
                resolved[name] = data_bag.get_item(path)
        result = func(**resolved)
        if isinstance(result, dict):
            result = Bag(source=result)
        return result

    def _background_load(self) -> None:
        """Background refresh: recompute and notify data subscribers.

        Overrides BagResolver._background_load to trigger data change
        events via node.set_value(). The base implementation writes
        to cached_value (which maps to node._value) silently.
        We use set_value() instead to trigger subscriber events.
        """
        from datetime import datetime

        result = self.load()
        if isinstance(result, dict):
            result = Bag(source=result)
        self._cache_last_update = datetime.now()
        node = self._parent_node
        if node is not None:
            node.set_value(result)
            # cached_value reads from node._value (set by set_value above)
        else:
            self._cached_value = result
