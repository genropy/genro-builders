# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""ComponentProxy - transparent proxy returned by component calls.

Wraps the parent Bag (root) and optional named slot Bags.
Attribute access is delegated to root, except for slot names
which return the corresponding slot Bag.

This allows uniform usage whether or not a component has slots:

Without slots (backward-compatible)::

    page.login_form()       # returns proxy, delegates to parent bag
    page.other_element()    # chaining works via proxy

With slots::

    shell = page.app_shell(title='My App')
    shell.left.tree(store=data)     # populates 'left' slot Bag
    shell.right.content('Main')     # populates 'right' slot Bag
    shell.toolbar('Actions')        # delegates to root (parent bag)
"""
from __future__ import annotations

from typing import Any


class ComponentProxy:
    """Transparent proxy for component calls with optional named slots.

    Delegates attribute access to root Bag. Slot names are intercepted
    and return the corresponding slot Bag instead.

    Args:
        root: The parent Bag (destination_bag) for chaining.
        slots: Dict mapping slot names to empty BuilderBag instances.
    """

    def __init__(self, root: Any, slots: dict[str, Any] | None = None) -> None:
        object.__setattr__(self, "_root", root)
        object.__setattr__(self, "_slots", slots or {})

    def __getattr__(self, name: str) -> Any:
        slots = object.__getattribute__(self, "_slots")
        if name in slots:
            return slots[name]
        root = object.__getattribute__(self, "_root")
        return getattr(root, name)

    def __setattr__(self, name: str, value: Any) -> None:
        root = object.__getattribute__(self, "_root")
        setattr(root, name, value)

    def __getitem__(self, key: Any) -> Any:
        root = object.__getattribute__(self, "_root")
        return root[key]

    def __setitem__(self, key: Any, value: Any) -> None:
        root = object.__getattribute__(self, "_root")
        root[key] = value

    def __len__(self) -> int:
        root = object.__getattribute__(self, "_root")
        return len(root)

    def __iter__(self) -> Any:
        root = object.__getattribute__(self, "_root")
        return iter(root)

    def __repr__(self) -> str:
        slots = object.__getattribute__(self, "_slots")
        root = object.__getattribute__(self, "_root")
        if slots:
            slot_names = ", ".join(sorted(slots))
            return f"<ComponentProxy slots=[{slot_names}] root={root!r}>"
        return f"<ComponentProxy root={root!r}>"
