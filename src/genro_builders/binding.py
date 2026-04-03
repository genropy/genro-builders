# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BindingManager — reactive data binding for ^pointer subscriptions.

Manages the flat subscription map and reactive notifications. The map is
populated during the build phase; the BindingManager handles data change
notifications and signals re-render (without modifying the built Bag).

Subscription map structure (flat, string-only):
    {data_key → [built_entry, ...]}

Where:
    data_key: absolute data path, optionally with ?attr
              (e.g., 'user.name', 'theme.btn?color')
    built_entry: absolute built node path, optionally with ?attr
              to indicate where to write the value
              (e.g., 'heading_0', 'widget_2?bg')

Example:
    >>> manager = BindingManager()
    >>> manager.subscribe(built_bag, data)
    >>> manager.register("user.name", "heading_0")
    >>> data['user.name'] = 'Giovanni'  # triggers update on heading_0
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import Any

from genro_bag import Bag, BagNode


class BindingManager:
    """Manages the subscription map and reactive notifications.

    Entries are registered during the build phase. The BindingManager
    subscribes to data changes and signals re-render via the
    on_node_updated callback. The built Bag is never modified.
    """

    def __init__(self, on_node_updated: Callable[[BagNode], None] | None = None):
        """Initialize the binding manager.

        Args:
            on_node_updated: Optional callback invoked when a bound node
                is updated due to a data change. Receives the updated node.
        """
        self._subscription_map: dict[str, list[str]] = defaultdict(list)
        self._built: Bag | None = None
        self._data: Bag | None = None
        self._subscriber_id = "genro_builders_binding"
        self._on_node_updated = on_node_updated

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
        """Signal that a built node needs re-render.

        The built node is NOT modified — ^pointer strings stay.
        The renderer resolves values just-in-time from data.
        """
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

    def _update_bound_nodes(self, data_key: str, reason: str | None = None) -> None:
        """Notify all built nodes bound to a specific data key.

        The built Bag is NOT modified — ^pointer strings stay.
        Only signals re-render via _on_node_updated callback.

        Args:
            data_key: The data key that changed.
            reason: Optional built path of the node that originated the change.
                    Used for anti-loop: skip if built entry matches reason.
        """
        entries = self._subscription_map.get(data_key, [])
        if not entries or self._data is None or self._built is None:
            return

        for built_entry in entries:
            node_path = built_entry.partition("?")[0]
            if reason and node_path == reason:
                continue

            self._notify_node(built_entry)
