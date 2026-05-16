# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Builder-aware Bag and BagNode — level 1 of the bag/node layering.

Decision 3: ``BuilderBag`` and ``BuilderBagNode`` are obtained by
combining ``Bag`` with ``_BuilderBagMixin`` and ``BagNode`` with
``_BuilderBagNodeMixin``. The grammar-aware logic lives in the mixins;
the base classes from ``genro-bag`` stay untouched.

Decision 10: every node carries two slots, ``_builder`` and
``_handler``. ``_builder`` is the active dialect for that node;
``_handler`` is the BuilderHandler that owns the tree. They are set
at attach time. Immutability is convention-only during the restart
(see ``feedback_lightweight_nodes.md``).

Decision 12: this module defines only level 1 (base common across
all role specializations). Level 2 (``BuilderSource`` and future
``BuilderData``, ...) lives in dedicated modules.
"""
from __future__ import annotations

from typing import Any

from genro_bag import Bag, BagNode

_BUILDERBAG_PROTECTED = frozenset({"node_class"})


class _BuilderBagNodeMixin:
    """Builder-aware logic for nodes: schema dispatch via __getattr__.

    The actual slots ``_builder``/``_handler`` are declared on the
    final ``BuilderBagNode`` class (BagNode itself uses __slots__,
    so the slots must live on the concrete class to avoid a layout
    conflict).
    """

    __slots__ = ()

    def _resolve_builder(self) -> Any:
        """Return the active builder, falling back to the parent bag.

        Nodes are not always attached with their slots populated (e.g.
        when created via plain ``Bag.set_item``). The slot acts as a
        cache; if empty, look it up on the containing bag.
        """
        try:
            value = object.__getattribute__(self, "_builder")
        except AttributeError:
            value = None
        if value is not None:
            return value
        parent = self._parent_bag
        return getattr(parent, "_builder", None) if parent is not None else None

    def __getattr__(self, name: str) -> Any:
        """Delegate unknown attribute access to the active builder.

        ``node.div('hello')`` becomes ``builder._command_on_node(...)``
        when the active builder carries a tag named ``div`` in its
        schema.
        """
        if name.startswith("_"):
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            )
        builder = self._resolve_builder()
        if builder is None or name not in builder._schema_tag_names:
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            )
        return lambda node_value=None, node_position=None, **attrs: builder._command_on_node(
            self, name,
            node_position=node_position, node_value=node_value, **attrs,
        )

    def __dir__(self) -> list[str]:
        """Expose schema tag names for autocompletion."""
        base = set(super().__dir__())
        builder = self._resolve_builder()
        if builder is not None:
            base.update(builder._schema_tag_names)
        return sorted(base)


class _BuilderBagMixin:
    """Builder-aware logic for bags: schema dispatch via __getattribute__.

    Bag itself does not use __slots__, so ``_builder``/``_handler``
    live in ``__dict__`` on the concrete class.
    """

    __slots__ = ()

    def __getattribute__(self, name: str) -> Any:
        """Resolve attribute lookup with grammar priority.

        Order:
            1. dunder / private → normal lookup (fast path).
            2. infrastructure names (``node_class``) → normal.
            3. ``bag_<name>`` → strip prefix and look up the underlying Bag.
            4. ``_builder`` set and ``name`` in its schema → grammar dispatch.
            5. fallback to normal lookup.
        """
        if name.startswith("_"):
            return super().__getattribute__(name)
        if name in _BUILDERBAG_PROTECTED:
            return super().__getattribute__(name)
        if name.startswith("bag_"):
            return super().__getattribute__(name[4:])
        try:
            builder = super().__getattribute__("_builder")
        except AttributeError:
            builder = None
        if builder is not None and name in builder._schema_tag_names:
            return builder._bag_call(self, name)
        return super().__getattribute__(name)

    def __dir__(self) -> list[str]:
        """Expose schema tag names alongside the regular Bag API."""
        base = set(super().__dir__())
        builder = getattr(self, "_builder", None)
        if builder is not None:
            base.update(builder._schema_tag_names)
        return sorted(base)


class BuilderBagNode(BagNode, _BuilderBagNodeMixin):
    """Level-1 node: BagNode with builder-aware attribute dispatch.

    Source-side and built-side nodes inherit from this (decision 12).
    """

    __slots__ = ("_builder", "_handler")


class BuilderBag(Bag, _BuilderBagMixin):
    """Level-1 bag: Bag with builder-aware attribute dispatch.

    Source-side and built-side bags inherit from this (decision 12).
    Level-1 bags are not instantiated directly in normal flows; the
    handler uses level-2 subclasses.
    """

    node_class: type[BagNode] = BuilderBagNode

    def __init__(
        self,
        source: dict[str, Any] | None = None,
        *,
        builder: Any = None,
        handler: Any = None,
    ):
        """Initialize the bag and attach the active builder/handler.

        Args:
            source: Optional dict to seed the Bag (mirrors ``Bag.__init__``).
            builder: BagBuilderBase instance whose schema drives attribute
                dispatch on this bag (and on nodes attached to it).
            handler: BuilderHandler that owns the tree this bag belongs to.
        """
        super().__init__(source=source)
        self._builder = builder
        self._handler = handler
