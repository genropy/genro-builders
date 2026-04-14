# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""FormulaResolver — pull-based computed data values.

Installed on data store nodes by ``data_formula`` during build.
Computes value on-demand: when ``data['area']`` is read, the resolver
calls ``func(base=data['base'], altezza=data['altezza'])`` and returns
the result. No push, no cascade, no built-bag node.

Always ``read_only=True``: the resolver never stores its result in the
node's ``_value`` — every read triggers a fresh computation.
"""

from __future__ import annotations

from typing import Any

from genro_bag import Bag
from genro_bag.resolver import BagSyncResolver


class FormulaResolver(BagSyncResolver):
    """Resolver for computed data values (pull-based data_formula).

    Installed on data store nodes at build time. Reads dependencies
    from the same data Bag and calls func to produce the value.
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
