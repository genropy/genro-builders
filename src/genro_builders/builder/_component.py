# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Component infrastructure — proxy and mixin.

ComponentProxy: transparent proxy returned by component calls.
    Wraps the parent Bag (root) and optional named slot Bags (lazy).
    Attribute access delegates to root, except for slot names.
    Stored as node._value on the component source node, so the build
    walk can retrieve it to materialize the component.

_ComponentMixin: builder mixin for component handling.
    Owns _handle_component() — attaches a ComponentProxy to the node
    and returns it to the caller.
"""
from __future__ import annotations

from typing import Any

from genro_bag import Bag
from genro_toolbox.dict_utils import dictExtract

from ..builder_bag import BuilderBag

# ---------------------------------------------------------------------------
# ComponentProxy
# ---------------------------------------------------------------------------


class ComponentProxy:
    """Transparent proxy for component calls with optional named slots.

    Delegates attribute access to root Bag. Slot names are intercepted
    and return the corresponding slot Bag (created lazily on first access).

    Used as ``node._value`` on the component source node so the build
    walk can find it and materialize the component at build time.
    """

    def __init__(
        self,
        root: Any,
        slot_names: tuple[str, ...] | list[str] = (),
        component_name: str | None = None,
        builder: Any = None,
        user_main_kwargs: dict | None = None,
    ) -> None:
        object.__setattr__(self, "_root", root)
        object.__setattr__(self, "_slot_names", tuple(slot_names))
        object.__setattr__(self, "_slots", {})
        object.__setattr__(self, "_component_name", component_name)
        object.__setattr__(self, "_builder", builder)
        object.__setattr__(self, "_user_main_kwargs", user_main_kwargs or {})

    def set_backref(self, node: Any = None, parent: Any = None) -> None:
        """No-op. The proxy wraps the root bag; it does not participate
        in backref propagation on its own."""

    def clear_backref(self) -> None:
        """No-op. Symmetric with set_backref."""

    def __getattr__(self, name: str) -> Any:
        slot_names = object.__getattribute__(self, "_slot_names")
        if name in slot_names:
            slots = object.__getattribute__(self, "_slots")
            if name not in slots:
                builder = object.__getattribute__(self, "_builder")
                comp_name = object.__getattribute__(self, "_component_name")
                info = builder._get_schema_info(comp_name) if builder and comp_name else {}
                builder_class = info.get("component_builder") or (
                    type(builder) if builder else None
                )
                slots[name] = BuilderBag(builder=builder_class)
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
        slot_names = object.__getattribute__(self, "_slot_names")
        root = object.__getattribute__(self, "_root")
        base = set(dir(root))
        base.update(slot_names)
        return sorted(base)

    def __repr__(self) -> str:
        slot_names = object.__getattribute__(self, "_slot_names")
        root = object.__getattribute__(self, "_root")
        if slot_names:
            names = ", ".join(sorted(slot_names))
            return f"<ComponentProxy slots=[{names}] root={root!r}>"
        return f"<ComponentProxy root={root!r}>"


# ---------------------------------------------------------------------------
# _ComponentMixin
# ---------------------------------------------------------------------------


class _ComponentMixin:
    """Builder mixin for component handling.

    Owns the component lifecycle: attaches a ComponentProxy as the node
    value, returns the proxy to the caller for slot population.
    """

    def _handle_component(
        self,
        destination_bag: Bag,
        info: dict,
        node_tag: str,
        kwargs: dict,
    ) -> Any:
        """Handle component invocation.

        Creates a ComponentProxy and attaches it as node_value on the
        source node. The proxy carries the component identity
        (component_name + builder) plus optional user-supplied
        ``main_kwargs`` to be splatted on the main widget at build time.

        Extracts ``main_*`` prefixed kwargs and ``main_kwargs={...}`` from
        the user call (per contract §2bis.8): both forms are equivalent
        and the explicit ``main_kwargs`` dict wins on key collision. The
        residual kwargs (non-``main_*``) become attributes of the source
        node.

        The handler body is NOT called here. It is called by the build
        walk when it reaches the component source node.
        """
        kwargs.pop("node_value", None)
        node_label = kwargs.pop("node_label", None)
        node_position = kwargs.pop("node_position", None)

        explicit_main = kwargs.pop("main_kwargs", None) or {}
        prefixed_main = dictExtract(kwargs, "main_", pop=True, slice_prefix=True)
        user_main_kwargs = {**prefixed_main, **explicit_main}

        slot_names = info.get("slots") or []

        proxy = ComponentProxy(
            root=destination_bag,
            slot_names=slot_names,
            component_name=node_tag,
            builder=self,
            user_main_kwargs=user_main_kwargs,
        )

        node = self._add_element(
            destination_bag,
            node_value=proxy,
            node_tag=node_tag,
            node_label=node_label,
            node_position=node_position,
            **kwargs,
        )
        node.set_attr({"_is_component": True}, trigger=False)

        return proxy
