# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BindingManager — reactive data binding for ^pointer resolution.

Manages the subscription map between a store Bag (with ^pointers) and a
data Bag (source of values). When data changes, affected nodes are updated
automatically.

Subscription map structure:
    {(data_path, attr_or_none) → [(node, location), ...]}

Where:
    data_path: resolved absolute path in the data Bag
    attr_or_none: attribute name (from ?attr syntax) or None for value
    node: BagNode in the store/static Bag
    location: 'value' or 'attr:attribute_name'

Example:
    >>> manager = BindingManager()
    >>> manager.bind(static_bag, data)
    >>> data['user.name'] = 'Giovanni'  # triggers update on bound nodes
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from typing import Any

from genro_bag import Bag, BagNode

from .pointer import scan_for_pointers


class BindingManager:
    """Manages ^pointer binding between a store Bag and a data Bag.

    Builds a subscription map during bind(), subscribes to data changes,
    and updates bound nodes when data changes.
    """

    def __init__(self, on_node_updated: Callable[[BagNode], None] | None = None):
        """Initialize the binding manager.

        Args:
            on_node_updated: Optional callback invoked when a bound node
                is updated due to a data change. Receives the updated node.
        """
        self._subscription_map: dict[tuple[str, str | None], list[tuple[BagNode, str]]] = defaultdict(list)
        self._data: Bag | None = None
        self._subscriber_id = "genro_builders_binding"
        self._on_node_updated = on_node_updated

    @property
    def subscription_map(self) -> dict[tuple[str, str | None], list[tuple[BagNode, str]]]:
        """The current subscription map (read-only)."""
        return dict(self._subscription_map)

    def bind(self, bag: Bag, data: Bag) -> None:
        """Walk bag, find ^pointers, resolve them, build subscription map.

        Steps:
            1. Clear previous bindings
            2. Walk bag recursively
            3. For each ^pointer: resolve, apply, register in map
            4. Subscribe to data changes

        Args:
            bag: The materialized Bag to scan for ^pointers.
            data: The data Bag (source of values).
        """
        self.unbind()
        self._data = data

        self._walk_bind(bag, data)

        # Subscribe to data changes for reactive updates
        if not data.backref:
            data.set_backref()
        data.subscribe(self._subscriber_id, any=self._on_data_changed)

    def unbind(self) -> None:
        """Remove all subscriptions and clear the map."""
        if self._data is not None:
            self._data.unsubscribe(self._subscriber_id, any=True)
        self._subscription_map.clear()
        self._data = None

    def unbind_path(self, path: str) -> None:
        """Remove all subscription entries for nodes at or under the given path.

        Args:
            path: The store path to unbind (e.g., 'page.header').
                  All nodes whose compiled path equals or starts with this path
                  are removed from the subscription map.
        """
        to_remove: list[tuple[str, str | None]] = []
        for map_key, entries in self._subscription_map.items():
            remaining = [
                (target_node, location)
                for target_node, location in entries
                if not self._node_under_path(target_node, path)
            ]
            if remaining:
                self._subscription_map[map_key] = remaining
            else:
                to_remove.append(map_key)
        for key in to_remove:
            del self._subscription_map[key]

    def _node_under_path(self, node: BagNode, path: str) -> bool:
        """Check if a node's compiled path is at or under the given path."""
        node_path = node.compiled.get("path", "")
        return node_path == path or node_path.startswith(path + ".")

    def bind_subtree(self, node: BagNode, data: Bag, path: str) -> None:
        """Bind ^pointers on a single node and its children.

        Used for incremental compilation after a node is inserted
        into the compiled bag. Binds only this subtree without
        re-scanning the entire tree.

        Args:
            node: The compiled BagNode to bind.
            data: The data Bag for pointer resolution.
            path: The path of this node in the compiled bag.
        """
        node.compiled["path"] = path
        pointers = scan_for_pointers(node)
        if pointers:
            self._bind_node(node, pointers, data)

        value = node.static_value
        if isinstance(value, Bag):
            self._walk_bind(value, data, prefix=path)

    def rebind(self, data: Bag) -> None:
        """Re-resolve all pointers against new data.

        Uses stored binding info on nodes (node.compiled['bindings'])
        to re-resolve without re-scanning the tree.

        Args:
            data: The new data Bag.
        """
        if self._data is not None:
            self._data.unsubscribe(self._subscriber_id, any=True)

        self._data = data
        if not data.backref:
            data.set_backref()

        for entries in self._subscription_map.values():
            for node, location in entries:
                bindings = node.compiled.get("bindings", [])
                for binding_info in bindings:
                    if binding_info["location"] == location:
                        self._apply_value(
                            node, binding_info["pointer_info"], location, data,
                            binding_info["datapath"], trigger=False,
                        )

        data.subscribe(self._subscriber_id, any=self._on_data_changed)

    # -------------------------------------------------------------------------
    # Internal
    # -------------------------------------------------------------------------

    def _walk_bind(self, bag: Bag, data: Bag, prefix: str = "") -> None:
        """Recursively walk bag and bind ^pointers."""
        for node in bag:
            path = f"{prefix}.{node.label}" if prefix else node.label
            node.compiled["path"] = path
            pointers = scan_for_pointers(node)
            if pointers:
                self._bind_node(node, pointers, data)

            # Recurse into children
            value = node.static_value
            if isinstance(value, Bag):
                self._walk_bind(value, data, prefix=path)

    def _bind_node(
        self,
        node: BagNode,
        pointers: list[tuple[Any, str]],
        data: Bag,
    ) -> None:
        """Bind all ^pointers found on a single node."""
        node.compiled["bindings"] = []

        for pointer_info, location in pointers:
            # Resolve datapath for relative pointers
            datapath = ""
            if pointer_info.is_relative and hasattr(node, "_resolve_datapath"):
                datapath = node._resolve_datapath()

            # Compute absolute data path
            data_path = pointer_info.path
            if pointer_info.is_relative:
                rel = data_path[1:]  # strip leading '.'
                data_path = f"{datapath}.{rel}" if datapath else rel

            # Resolve and apply current value
            self._apply_value(node, pointer_info, location, data, datapath, trigger=False)

            # Register in subscription map
            map_key = (data_path, pointer_info.attr)
            self._subscription_map[map_key].append((node, location))

            # Store binding info on node for rebind
            node.compiled["bindings"].append({
                "pointer_info": pointer_info,
                "location": location,
                "datapath": datapath,
                "data_path": data_path,
            })

    def _apply_value(
        self,
        node: BagNode,
        pointer_info: Any,
        location: str,
        data: Bag,
        datapath: str,
        trigger: bool = False,
    ) -> None:
        """Resolve a pointer and apply the value to the node."""
        if hasattr(node, "_get_relative_data"):
            resolved = node._get_relative_data(data, pointer_info.raw[1:])  # strip ^
        else:
            # Fallback: direct data access
            data_path = pointer_info.path
            if pointer_info.is_relative:
                rel = data_path[1:]
                data_path = f"{datapath}.{rel}" if datapath else rel
            if pointer_info.attr:
                data_node = data.get_node(data_path)
                resolved = data_node.attr.get(pointer_info.attr) if data_node else None
            else:
                resolved = data.get_item(data_path)

        if location == "value":
            node.set_value(resolved, trigger=trigger)
        elif location.startswith("attr:"):
            attr_name = location[5:]
            node.set_attr({attr_name: resolved}, trigger=trigger)

    def _on_data_changed(
        self,
        node: BagNode | None = None,
        pathlist: list | None = None,
        oldvalue: Any = None,
        evt: str = "",
        **kwargs: Any,
    ) -> None:
        """Callback from data.subscribe — update affected bound nodes.

        Args:
            node: The data node that changed.
            pathlist: Path components from data root to changed node.
            oldvalue: Previous value.
            evt: Event type ('upd_value', 'upd_attrs', 'ins', 'del').
        """
        if pathlist is None or self._data is None:
            return

        changed_path = ".".join(str(p) for p in pathlist)

        if evt == "upd_attrs":
            # Attribute change: check each changed attr
            changed_attrs = oldvalue if isinstance(oldvalue, list) else []
            for attr_name in changed_attrs:
                self._update_bound_nodes((changed_path, attr_name))
        else:
            # Value change
            self._update_bound_nodes((changed_path, None))

    def _update_bound_nodes(self, map_key: tuple[str, str | None]) -> None:
        """Update all nodes bound to a specific data path."""
        entries = self._subscription_map.get(map_key, [])
        for target_node, location in entries:
            bindings = target_node.compiled.get("bindings", [])
            for binding_info in bindings:
                if binding_info["location"] == location:
                    self._apply_value(
                        target_node, binding_info["pointer_info"], location,
                        self._data, binding_info["datapath"], trigger=True,
                    )
                    if self._on_node_updated:
                        self._on_node_updated(target_node)
                    break
