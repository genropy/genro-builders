# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Pointer utilities and reactive binding (pull model).

Pointer syntax:
    ^alfa.beta        — absolute path to data value
    ^.beta            — relative to current node's datapath
    ^alfa.beta?color  — attribute 'color' of data node 'alfa.beta'

Functions:
    is_pointer(value)       — True if value is a ^pointer string
    parse_pointer(raw)      — extract path, attr, is_relative from raw string
    scan_for_pointers(node) — find all ^pointers in node value and attributes

BindingManager:
    Subscribes to data changes and signals "dirty" to the caller
    via callback. No per-node dispatch — the caller (ReactivityEngine
    or manager) decides what to do.

    Maintains a list of reactive nodes (UI nodes with ^pointers) for
    future use by partial compile. The list is NOT used for dispatch.

3-level path matching (utility, used by compiler for partial recompile):
    1. **node** — exact match (pointer path == changed path)
    2. **container** — ancestor changed (changed path is prefix of pointer path)
    3. **child** — descendant changed (pointer path is prefix of changed path)
"""
from __future__ import annotations

import contextlib
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
# Path matching utility (for compiler partial recompile)
# ---------------------------------------------------------------------------


def get_trigger_reason(watched_path: str, changed_path: str) -> str | None:
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


# ---------------------------------------------------------------------------
# BindingManager (pull model: any data change → callback)
# ---------------------------------------------------------------------------


class BindingManager:
    """Subscribes to data changes and signals dirty via callback.

    No per-node dispatch. The callback receives the changed path
    for potential use by partial compile.

    Maintains a list of reactive nodes (UI nodes with ^pointers)
    for future partial compile optimization.
    """

    def __init__(
        self,
        on_data_changed: Callable[[str], None] | None = None,
    ):
        self._reactive_nodes: list[BagNode] = []
        self._built: Bag | None = None
        self._data: Bag | None = None
        self._subscriber_id = "genro_builders_binding"
        self._on_data_changed_callback = on_data_changed

    @property
    def reactive_nodes(self) -> list[BagNode]:
        """The current list of reactive nodes (read-only copy)."""
        return list(self._reactive_nodes)

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    def subscribe(self, built: Bag, data: Bag) -> None:
        """Subscribe to data changes.

        Walks the built Bag and collects UI nodes with ^pointers.
        Subscribes to any data change → callback.
        """
        self._built = built
        self._data = data

        self._reactive_nodes = []
        self._collect_reactive_nodes(built)

        if not data.backref:
            data.set_backref()
        data.subscribe(self._subscriber_id, any=self._on_data_changed)

    def _collect_reactive_nodes(self, bag: Bag) -> None:
        """Walk the built bag and collect nodes with ^pointers."""
        for node in bag:
            if scan_for_pointers(node):
                self._reactive_nodes.append(node)
            value = node.get_value(static=True)
            if isinstance(value, Bag):
                self._collect_reactive_nodes(value)

    def register_node(self, node: BagNode) -> None:
        """Add a node to the reactive list if it has ^pointers."""
        if scan_for_pointers(node) and node not in self._reactive_nodes:
            self._reactive_nodes.append(node)

    def unregister_node(self, node: BagNode) -> None:
        """Remove a node from the reactive list."""
        with contextlib.suppress(ValueError):
            self._reactive_nodes.remove(node)

    def unbind(self) -> None:
        """Remove all subscriptions, clear reactive nodes."""
        if self._data is not None:
            self._data.unsubscribe(self._subscriber_id, any=True)
        self._reactive_nodes.clear()
        self._built = None
        self._data = None

    # -------------------------------------------------------------------------
    # Internal
    # -------------------------------------------------------------------------

    def _on_data_changed(
        self,
        node: BagNode | None = None,
        pathlist: list | None = None,
        oldvalue: Any = None,
        evt: str = "",
        **kwargs: Any,
    ) -> None:
        """Callback from data.subscribe — signal dirty."""
        if pathlist is None:
            return
        changed_path = ".".join(str(p) for p in pathlist)
        if self._on_data_changed_callback:
            self._on_data_changed_callback(changed_path)
