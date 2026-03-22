# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Component expander - walk with automatic component expansion.

With ComponentResolver, expansion is automatic: components store a resolver
that executes the handler lazily. To expand, just walk with static=False.

Example:
    >>> from genro_bag import Bag
    >>> from genro_bag.expander import expand
    >>>
    >>> # bag contains components (e.g., lasagne_sauce -> meat_sauce -> soffritto)
    >>> for path, node in expand(bag):
    ...     # Components are expanded via their resolvers
    ...     print(f"{path}: {node.tag}")
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from genro_bag import Bag, BagNode


def expand(bag: Bag) -> Iterator[tuple[str, BagNode]]:
    """Expand components in a Bag during iteration.

    Simply delegates to bag.walk(static=False), which triggers ComponentResolvers
    to expand component nodes automatically.

    Args:
        bag: The Bag to iterate with expansion.

    Yields:
        Tuples of (path, node) where components have been expanded.

    Example:
        >>> for path, node in expand(menu_bag):
        ...     if node.tag == "ingredient":
        ...         print(f"{path}: {node.value}")
    """
    yield from bag.walk(static=False)
