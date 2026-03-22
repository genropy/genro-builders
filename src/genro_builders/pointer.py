# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Pointer utilities for ^path syntax detection and parsing.

Pointer syntax:
    ^alfa.beta        — absolute path to data value
    ^.beta            — relative to current node's datapath
    ^alfa.beta?color  — attribute 'color' of data node 'alfa.beta'

Functions:
    is_pointer(value)       — True if value is a ^pointer string
    parse_pointer(raw)      — extract path, attr, is_relative from raw string
    scan_for_pointers(node) — find all ^pointers in node value and attributes
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


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
