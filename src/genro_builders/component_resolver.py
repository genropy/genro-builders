# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""ComponentResolver - lazy expansion of components via BagResolver.

A ComponentResolver is attached to each component node at creation time.
When the node is accessed with static=False (via walk, expand, or compile),
the resolver executes the component handler body and returns the populated Bag.

Supports component inheritance via ``based_on``: a derived component receives
the Bag already populated by its parent component, then applies its own
modifications.

Example:
    >>> class MyBuilder(BagBuilderBase):
    ...     @component()
    ...     def base_form(self, comp, **kwargs):
    ...         comp.input(name='field1')
    ...
    ...     @component(based_on='base_form')
    ...     def extended_form(self, comp, **kwargs):
    ...         comp.input(name='field2')  # adds to base_form content
"""
from __future__ import annotations

from typing import Any

from genro_bag import Bag
from genro_bag.resolver import BagResolver


class ComponentResolver(BagResolver):
    """Resolver for lazy component expansion.

    Attached to component nodes by _handle_component(). Executes the
    handler body on first non-static access and returns the populated Bag.

    With ``based_on``, resolves the parent component first, then passes
    the already-populated Bag to the current handler for modification.

    Attributes (via class_kwargs):
        handler: The component handler callable (bound method on builder).
        builder_class: Builder class for creating the component's internal Bag.
        based_on: Name of the parent component (for inheritance chain).
        builder: Builder instance (needed to resolve based_on via schema).
    """

    class_kwargs: dict[str, Any] = {
        "cache_time": 0,
        "read_only": True,
        "handler": None,
        "builder_class": None,
        "based_on": None,
        "builder": None,
    }
    class_args: list[str] = []
    internal_params: set[str] = {
        "cache_time", "read_only", "retry_policy", "as_bag",
        "handler", "builder_class", "based_on", "builder",
    }

    def load(self) -> Bag:
        """Execute the component handler and return the populated Bag.

        If based_on is set, resolves the parent component first (recursively),
        then passes the result to the current handler for modification.
        """
        handler = self._kw["handler"]
        builder_class = self._kw["builder_class"]
        based_on = self._kw["based_on"]
        builder_instance = self._kw["builder"]

        # Collect kwargs from parent node attributes
        kwargs = dict(self._parent_node.attr) if self._parent_node else {}

        if based_on:
            # Resolve parent component first
            comp_bag = self._resolve_parent(based_on, builder_instance, kwargs)
        else:
            from .builder_bag import BuilderBag

            comp_bag = BuilderBag(builder=builder_class)

        # Call the current handler (modifies comp_bag in place)
        if handler:
            handler(comp_bag, **kwargs)

        return comp_bag

    def _resolve_parent(
        self, based_on: str, builder_instance: Any, kwargs: dict[str, Any],
    ) -> Bag:
        """Resolve the parent component, handling recursive based_on chains."""
        from .builder_bag import BuilderBag

        parent_info = builder_instance.get_schema_info(based_on)
        parent_handler_name = parent_info.get("handler_name")
        parent_handler = getattr(builder_instance, parent_handler_name) if parent_handler_name else None
        parent_builder_class = parent_info.get("component_builder") or type(builder_instance)
        parent_based_on = parent_info.get("based_on")

        if parent_based_on:
            # Recursive: parent is also based on another component
            comp_bag = self._resolve_parent(parent_based_on, builder_instance, kwargs)
        else:
            comp_bag = BuilderBag(builder=parent_builder_class)

        if parent_handler:
            parent_handler(comp_bag, **kwargs)

        return comp_bag
