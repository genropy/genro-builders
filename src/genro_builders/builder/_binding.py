# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Pointer utilities and reactive binding for ^pointer subscriptions.

Pointer syntax:
    ^alfa.beta        — absolute path to data value
    ^.beta            — relative to current node's datapath
    ^alfa.beta?color  — attribute 'color' of data node 'alfa.beta'

Functions:
    is_pointer(value)       — True if value is a ^pointer string
    parse_pointer(raw)      — extract path, attr, is_relative from raw string
    scan_for_pointers(node) — find all ^pointers in node value and attributes

BindingManager:
    Manages the flat subscription map and 3-level reactive notifications.
    The map is populated during the build phase by ``_register_bindings``;
    the BindingManager handles data change notifications and signals
    re-render (without modifying the built Bag — pointers stay formal).

3-level propagation:
    When a data node changes, the BindingManager determines which
    subscribed entries are affected using an internal classification:
    1. **node** — the exact data path that changed.
    2. **container** — the changed path is an ancestor of the watched path.
    3. **child** — the changed path is a descendant of the watched path.

    All three levels trigger notification. The ``on_node_updated``
    callback receives only the affected BagNode, not the reason.

Subscription map structure (flat, string-only):
    {data_key -> [built_entry, ...]}

Where:
    data_key: absolute data path, optionally with ``?attr``
              (e.g., ``'user.name'``, ``'theme.btn?color'``)
    built_entry: absolute built node path, optionally with ``?attr``
              to indicate where to write the value
              (e.g., ``'heading_0'``, ``'widget_2?bg'``)

Formal pointers:
    The built Bag retains ``^pointer`` strings verbatim. Resolution
    happens just-in-time during render/compile via
    ``node.runtime_attrs`` / ``node.runtime_value``. The BindingManager
    only tracks *which* data paths affect *which* built paths — it never
    writes resolved values into the built Bag.

Example:
    >>> manager = BindingManager()
    >>> manager.subscribe(built_bag, data)
    >>> manager.register("user.name", "heading_0")
    >>> data['user.name'] = 'Giovanni'  # triggers update on heading_0
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from genro_bag import Bag, BagNode

# ---------------------------------------------------------------------------
# Pointer utilities
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PointerInfo:
    """Parsed ^pointer information.

    Attributes:
        raw: The original string (e.g., '^alfa.beta?color').
        path: The data path without ^ prefix (e.g., 'alfa.beta').
        attr: The attribute name after ? (e.g., 'color'), or None.
        is_relative: True if path starts with '.' (relative to datapath).
    """

    raw: str
    path: str
    attr: str | None
    is_relative: bool


def is_pointer(value: Any) -> bool:
    """Check if a value is a ^pointer string."""
    return isinstance(value, str) and value.startswith("^")


def parse_pointer(raw: str) -> PointerInfo:
    """Parse a ^pointer string into its components.

    Args:
        raw: The raw pointer string (must start with '^').

    Returns:
        PointerInfo with path, attr, and is_relative.

    Example:
        >>> parse_pointer('^alfa.beta?color')
        PointerInfo(raw='^alfa.beta?color', path='alfa.beta', attr='color', is_relative=False)
        >>> parse_pointer('^.name')
        PointerInfo(raw='^.name', path='.name', attr=None, is_relative=True)
    """
    body = raw[1:]  # strip ^

    attr = None
    if "?" in body:
        body, attr = body.split("?", 1)

    is_relative = body.startswith(".")

    return PointerInfo(raw=raw, path=body, attr=attr, is_relative=is_relative)


def scan_for_pointers(node: Any) -> list[tuple[PointerInfo, str]]:
    """Scan a node's value and attributes for ^pointers.

    Args:
        node: A BagNode to scan.

    Returns:
        List of (PointerInfo, location) tuples where location is
        'value' or 'attr:attribute_name'.
    """
    results: list[tuple[PointerInfo, str]] = []

    # Check node value
    value = node.static_value if hasattr(node, "static_value") else getattr(node, "_value", None)
    if is_pointer(value):
        results.append((parse_pointer(value), "value"))

    # Check attributes
    attr_dict = node.attr if hasattr(node, "attr") else {}
    for attr_name, attr_value in attr_dict.items():
        if attr_name.startswith("_"):
            continue
        if is_pointer(attr_value):
            results.append((parse_pointer(attr_value), f"attr:{attr_name}"))

    return results


# ---------------------------------------------------------------------------
# BindingManager
# ---------------------------------------------------------------------------


class BindingManager:
    """Manages the subscription map and reactive notifications.

    Entries are registered during the build phase. The BindingManager
    subscribes to data changes and signals re-render via the
    on_node_updated callback. The built Bag is never modified.
    """

    def __init__(
        self,
        on_node_updated: Callable[[BagNode], None] | None = None,
        on_formulas_triggered: Callable[[set[str], Any], None] | None = None,
    ):
        self._subscription_map: dict[str, list[str]] = defaultdict(list)
        self._built: Bag | None = None
        self._data: Bag | None = None
        self._subscriber_id = "genro_builders_binding"
        self._on_node_updated = on_node_updated
        self._on_formulas_triggered = on_formulas_triggered

    @property
    def subscription_map(self) -> dict[str, list[str]]:
        """The current subscription map (read-only)."""
        return dict(self._subscription_map)

    # -------------------------------------------------------------------------
    # Map registration
    # -------------------------------------------------------------------------

    def register(self, data_key: str, built_entry: str) -> None:
        """Register a subscription entry in the map.

        Called during the build phase for each ^pointer found.

        Args:
            data_key: Data path, optionally with ?attr suffix.
            built_entry: Built node path, optionally with ?attr suffix.
        """
        self._subscription_map[data_key].append(built_entry)

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    def subscribe(self, built: Bag, data: Bag) -> None:
        """Subscribe to data changes for reactive updates.

        Called after all entries have been registered in the map.

        Args:
            built: The built Bag (target for updates).
            data: The data Bag (source of values).
        """
        self._built = built
        self._data = data

        if not data.backref:
            data.set_backref()
        data.subscribe(self._subscriber_id, any=self._on_data_changed)

    def unbind(self) -> None:
        """Remove all subscriptions and clear the map."""
        if self._data is not None:
            self._data.unsubscribe(self._subscriber_id, any=True)
        self._subscription_map.clear()
        self._built = None
        self._data = None

    def unbind_path(self, path: str) -> None:
        """Remove all subscription entries for nodes at or under the given path.

        Args:
            path: The built path to unbind (e.g., 'page.header').
        """
        to_remove: list[str] = []
        for data_key, entries in self._subscription_map.items():
            remaining = [
                e for e in entries
                if not self._built_path_under(e, path)
            ]
            if remaining:
                self._subscription_map[data_key] = remaining
            else:
                to_remove.append(data_key)
        for key in to_remove:
            del self._subscription_map[key]

    def rebind(self, data: Bag) -> None:
        """Switch to new data and trigger re-render.

        The built Bag is NOT modified — ^pointer strings stay.
        The next render will resolve pointers from the new data.

        Args:
            data: The new data Bag.
        """
        if self._data is not None:
            self._data.unsubscribe(self._subscriber_id, any=True)

        self._data = data
        if not data.backref:
            data.set_backref()

        if self._built is not None:
            for built_entries in self._subscription_map.values():
                for built_entry in built_entries:
                    self._notify_node(built_entry)

        data.subscribe(self._subscriber_id, any=self._on_data_changed)

    # -------------------------------------------------------------------------
    # Internal
    # -------------------------------------------------------------------------

    def _notify_node(self, built_entry: str) -> None:
        """Signal that a built node needs re-render."""
        if self._built is None:
            return
        node_path = built_entry.partition("?")[0]
        if self._on_node_updated:
            target_node = self._built.get_node(node_path)
            if target_node:
                self._on_node_updated(target_node)

    def _built_path_under(self, built_entry: str, prefix: str) -> bool:
        """Check if a built entry's path is at or under the given prefix."""
        node_path = built_entry.partition("?")[0]
        return node_path == prefix or node_path.startswith(prefix + ".")

    def _on_data_changed(
        self,
        node: BagNode | None = None,
        pathlist: list | None = None,
        oldvalue: Any = None,
        evt: str = "",
        **kwargs: Any,
    ) -> None:
        """Callback from data.subscribe — update affected bound nodes."""
        if pathlist is None or self._data is None:
            return

        changed_path = ".".join(str(p) for p in pathlist)
        reason = kwargs.get("reason")

        if evt == "upd_attrs":
            changed_attrs = oldvalue if isinstance(oldvalue, list) else []
            for attr_name in changed_attrs:
                self._update_bound_nodes(f"{changed_path}?{attr_name}", reason=reason)
        else:
            self._update_bound_nodes(changed_path, reason=reason)

        if self._on_formulas_triggered:
            self._on_formulas_triggered({changed_path}, reason)

    def _update_bound_nodes(self, data_key: str, reason: str | None = None) -> None:
        """Notify all built nodes bound to a data key, with 3-level matching.

        For each subscription entry, determines the relationship between
        the watched path and the changed path:

            - node: exact match (watched == changed)
            - container: ancestor changed (watched starts with changed.)
            - child: descendant changed (changed starts with watched.)

        All three trigger a re-render notification.
        """
        if self._data is None or self._built is None:
            return

        changed_path = data_key.partition("?")[0]

        for watched_key, entries in self._subscription_map.items():
            watched_path = watched_key.partition("?")[0]

            trigger_reason = self._get_trigger_reason(watched_path, changed_path)
            if trigger_reason is None:
                # For attr-level keys, also check exact match on full key
                if watched_key == data_key:
                    trigger_reason = "node"
                else:
                    continue

            for built_entry in entries:
                node_path = built_entry.partition("?")[0]
                if reason and node_path == reason:
                    continue
                self._notify_node(built_entry)

    def _get_trigger_reason(
        self, watched_path: str, changed_path: str,
    ) -> str | None:
        """Determine relationship between watched and changed paths.

        Returns 'node', 'container', 'child', or None.

        - node: exact match
        - container: watched is a descendant of changed (ancestor changed)
        - child: changed is a descendant of watched (child changed)
        """
        if watched_path == changed_path:
            return "node"
        if watched_path.startswith(changed_path + "."):
            return "container"
        if changed_path.startswith(watched_path + "."):
            return "child"
        return None
