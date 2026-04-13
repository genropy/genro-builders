# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Component infrastructure — proxy and lazy resolver.

ComponentProxy: transparent proxy returned by component calls.
    Wraps the parent Bag (root) and optional named slot Bags.
    Attribute access delegates to root, except for slot names.

ComponentResolver: lazy expansion of components via BagResolver.
    Attached to component nodes at creation time. Executes the
    handler body on first non-static access (walk, expand, compile).
    Supports inheritance via ``based_on``.
"""
from __future__ import annotations

from typing import Any

from genro_bag import Bag
from genro_bag.resolver import BagResolver

# ---------------------------------------------------------------------------
# ComponentProxy
# ---------------------------------------------------------------------------


class ComponentProxy:
    """Transparent proxy for component calls with optional named slots.

    Delegates attribute access to root Bag. Slot names are intercepted
    and return the corresponding slot Bag instead.
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

    def __dir__(self) -> list[str]:
        """Return slot names plus root's dir for autocompletion."""
        slots = object.__getattribute__(self, "_slots")
        root = object.__getattribute__(self, "_root")
        base = set(dir(root))
        base.update(slots.keys())
        return sorted(base)

    def __repr__(self) -> str:
        slots = object.__getattribute__(self, "_slots")
        root = object.__getattribute__(self, "_root")
        if slots:
            slot_names = ", ".join(sorted(slots))
            return f"<ComponentProxy slots=[{slot_names}] root={root!r}>"
        return f"<ComponentProxy root={root!r}>"


# ---------------------------------------------------------------------------
# ComponentResolver
# ---------------------------------------------------------------------------


class ComponentResolver(BagResolver):
    """Resolver for lazy component expansion.

    Attached to component nodes by _handle_component(). Executes the
    handler body on first non-static access and returns the populated Bag.

    With ``based_on``, resolves the parent component first, then passes
    the already-populated Bag to the current handler for modification.
    """

    class_kwargs: dict[str, Any] = {
        "cache_time": 0,
        "read_only": True,
        "handler": None,
        "builder_class": None,
        "based_on": None,
        "builder": None,
        "slots": None,
    }
    class_args: list[str] = []
    internal_params: set[str] = {
        "cache_time", "read_only", "retry_policy", "as_bag",
        "handler", "builder_class", "based_on", "builder", "slots",
    }

    def load(self) -> Bag:
        """Execute the component handler and return the populated Bag."""
        handler = self._kw["handler"]
        builder_class = self._kw["builder_class"]
        based_on = self._kw["based_on"]
        builder_instance = self._kw["builder"]
        slots = self._kw.get("slots") or {}

        kwargs = dict(self._parent_node.attr) if self._parent_node else {}

        if based_on:
            comp_bag = self._resolve_parent(based_on, builder_instance, kwargs)
        else:
            from ..builder_bag import Component

            comp_bag = Component(builder=builder_class)
            comp_bag._skip_parent_validation = True

        result = None
        if handler:
            result = handler(comp_bag, **kwargs)

        # Mount slot content into destination Bags
        if slots and isinstance(result, dict):
            from genro_bag import BagNode

            for slot_name, dest in result.items():
                source_bag = slots.get(slot_name)
                if source_bag is None or len(source_bag) == 0:
                    continue

                if isinstance(dest, BagNode):
                    if not isinstance(dest.value, Bag):
                        from ..builder_bag import BuilderBag
                        dest.value = BuilderBag(builder=builder_class)
                    dest_bag = dest.value
                else:
                    dest_bag = dest

                for node in source_bag:
                    Bag.set_item(
                        dest_bag,
                        node.label,
                        node.value,
                        _attributes=dict(node.attr),
                        node_tag=node.node_tag,
                    )

        return comp_bag

    def _resolve_parent(
        self, based_on: str, builder_instance: Any, kwargs: dict[str, Any],
    ) -> Bag:
        """Resolve the parent component, handling recursive based_on chains."""
        from ..builder_bag import Component

        parent_info = builder_instance._get_schema_info(based_on)
        parent_handler_name = parent_info.get("handler_name")
        parent_handler = getattr(builder_instance, parent_handler_name) if parent_handler_name else None
        parent_builder_class = parent_info.get("component_builder") or type(builder_instance)
        parent_based_on = parent_info.get("based_on")

        if parent_based_on:
            comp_bag = self._resolve_parent(parent_based_on, builder_instance, kwargs)
        else:
            comp_bag = Component(builder=parent_builder_class)
            comp_bag._skip_parent_validation = True

        if parent_handler:
            parent_handler(comp_bag, **kwargs)

        return comp_bag
