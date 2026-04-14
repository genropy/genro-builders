# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Component infrastructure — proxy, resolver, and mixin.

ComponentProxy: transparent proxy returned by component calls.
    Wraps the parent Bag (root) and optional named slot Bags.
    Attribute access delegates to root, except for slot names.

ComponentResolver: lazy expansion of components via BagResolver.
    Attached to component nodes at creation time. Executes the
    handler body on first non-static access (walk, expand, compile).
    Supports inheritance via ``based_on``.

_ComponentMixin: builder mixin for component handling.
    Owns _handle_component() — creates ComponentResolver and
    ComponentProxy when a component tag is dispatched.
"""
from __future__ import annotations

from typing import Any

from genro_bag import Bag, BagNode
from genro_bag.resolver import BagSyncResolver

from ..builder_bag import BuilderBag, Component

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


class ComponentResolver(BagSyncResolver):
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
            comp_bag = Component(builder=builder_class)
            comp_bag._skip_parent_validation = True

        result = None
        if handler:
            result = handler(comp_bag, **kwargs)

        # Mount slot content into destination Bags
        if slots and isinstance(result, dict):
            for slot_name, dest in result.items():
                source_bag = slots.get(slot_name)
                if source_bag is None or len(source_bag) == 0:
                    continue

                if isinstance(dest, BagNode):
                    if not isinstance(dest.value, Bag):
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


# ---------------------------------------------------------------------------
# _ComponentMixin
# ---------------------------------------------------------------------------


class _ComponentMixin:
    """Builder mixin for component handling.

    Owns the component lifecycle: creates ComponentResolver for lazy
    expansion and returns ComponentProxy to the caller.
    """

    def _handle_component(
        self,
        destination_bag: Bag,
        info: dict,
        node_tag: str,
        kwargs: dict,
    ) -> Any:
        """Handle component invocation — lazy registration with resolver.

        Registers the component node with a ComponentResolver. The handler
        body is NOT called here — it will be called lazily when the node
        is accessed with static=False (during expand or compile).

        Returns a ComponentProxy that delegates to destination_bag.
        If the component has named slots, the proxy also provides access
        to slot Bags via attribute access.
        """
        kwargs.pop("node_value", None)
        node_label = kwargs.pop("node_label", None)
        node_position = kwargs.pop("node_position", None)

        node = self._add_element(
            destination_bag,
            node_value=None,
            node_tag=node_tag,
            node_label=node_label,
            node_position=node_position,
            **kwargs,
        )

        handler_name = info.get("handler_name")
        handler = getattr(self, handler_name) if handler_name else None
        builder_class = info.get("component_builder") or type(self)
        based_on = info.get("based_on")
        slot_names = info.get("slots") or []

        slots = {name: BuilderBag(builder=builder_class) for name in slot_names}

        resolver = ComponentResolver(
            handler=handler,
            builder_class=builder_class,
            based_on=based_on,
            builder=self,
            slots=slots if slots else None,
        )
        node.resolver = resolver

        return ComponentProxy(destination_bag, slots)
