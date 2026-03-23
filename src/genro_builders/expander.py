# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Component expander - flatten components into their expanded content.

Walks a Bag and transparently replaces component nodes (those with a
ComponentResolver) with their expanded children. The component wrapper
node itself does NOT appear in the output — only its contents.

Example:
    >>> from genro_builders.expander import expand
    >>>
    >>> # bag has: pasta (component) -> lasagne_sauce (component) -> ...
    >>> for path, node in expand(bag):
    ...     # Component wrappers are invisible, only leaf content appears
    ...     print(f"{path}: {node.node_tag}")
"""
from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

from genro_bag import Bag

if TYPE_CHECKING:
    from genro_bag import BagNode


def expand(bag: Bag) -> Iterator[tuple[str, BagNode]]:
    """Expand components in a Bag, yielding only non-component nodes.

    Component nodes (with resolver) are expanded and their children
    are yielded recursively. The component wrapper is not yielded.

    Args:
        bag: The Bag to iterate with expansion.

    Yields:
        Tuples of (path, node) for non-component nodes.
    """
    yield from _expand_walk(bag, "")


def _expand_walk(bag: Bag, prefix: str) -> Iterator[tuple[str, BagNode]]:
    """Recursive walk that flattens component nodes."""
    for node in bag:
        path = f"{prefix}.{node.label}" if prefix else node.label
        if node.resolver is not None:
            # Component: expand via resolver, don't yield the wrapper
            expanded = node.get_value(static=False)
            if isinstance(expanded, Bag):
                yield from _expand_walk(expanded, path)
        else:
            yield path, node
            value = node.get_value(static=True)
            if isinstance(value, Bag):
                yield from _expand_walk(value, path)
