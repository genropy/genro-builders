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


def _dispatch_struct_method(handler: Any, target: Any, name: str) -> Any | None:
    """Resolve ``name`` as a ``@struct_method`` on ``handler``.

    Returns a callable bound to ``target`` (bag or node) when the name
    matches a registered struct method on the handler; ``None`` if no
    match (caller falls through to whatever else it wants to try).
    """
    if handler is None:
        return None
    method_name = handler._struct_methods.get(name.lower())
    if method_name is None:
        return None
    bound = getattr(handler, method_name)
    return lambda *args, **kwargs: bound(target, *args, **kwargs)


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
        parent = self.parent_bag
        return getattr(parent, "_builder", None) if parent is not None else None

    def _resolve_handler(self) -> Any:
        """Return the handler that owns this tree, falling back to the parent bag."""
        try:
            value = object.__getattribute__(self, "_handler")
        except AttributeError:
            value = None
        if value is not None:
            return value
        parent = self.parent_bag
        return getattr(parent, "_handler", None) if parent is not None else None

    def _check_unique_id(self, node_id: Any) -> None:
        """Raise ValueError if ``node_id`` is already taken in this
        handler's source space. No-op when ``node_id`` is None.

        Called before adding a child, so the candidate id is checked
        against the existing tree only. Uniqueness scope is the owning
        handler (one node_id namespace per handler, subbuilders included).

        When the bag has no handler attached (off-line subtree built via
        ``BagBuilderBase.new_root``), the check is a no-op: uniqueness
        will be enforced — and is the user's responsibility to respect —
        only once the subtree is attached to a live source.
        """
        if node_id is None:
            return
        handler = self._resolve_handler()
        if handler is None:
            return
        try:
            handler.node_by_id(node_id)
        except KeyError:
            return
        raise ValueError(f"Duplicate node_id '{node_id}'.")

    def pointers(self) -> list[tuple[str, str]]:
        """Return the pointers carried by this node as ``(attrname, pointer)``.

        ``attrname=""`` for a pointer in ``node.value``, otherwise the
        attribute name. A pointer is any string starting with ``^``.
        Walks only this node — does not recurse into children.
        """
        result: list[tuple[str, str]] = [
            (attrname, v)
            for attrname, v in self.attr.items()
            if isinstance(v, str) and v.startswith("^")
        ]
        value = self.value
        if isinstance(value, str) and value.startswith("^"):
            result.append(("", value))
        return result

    def get_relative_data(
        self,
        path: str,
        autocreate: bool = False,
        default: Any = None,
    ) -> Any:
        """Read ``handler.data`` at ``path`` resolved relative to this node.

        ``path`` is composed via :meth:`BuilderHandler.abs_datapath`, so
        it accepts the same syntactic forms (absolute, relative ``.x``,
        ``#FORM``, ``#ANCHOR``, ``#<node_id>``, with or without the
        ``^``/``=`` prefix). The lookup is performed against the live
        ``handler.data`` Bag.

        When ``autocreate=True``, if the current value at ``path`` is
        ``None`` (either missing or explicitly stored as ``None``),
        ``default`` is written to ``handler.data`` before the read —
        the two cases are intentionally not distinguished (DBS-D1).
        """
        handler = self._resolve_handler()
        abs_path = handler.abs_datapath(self, path)
        if autocreate and handler.data.get_item(abs_path) is None:
            handler.data.set_item(abs_path, default)
        return handler.data.get_item(abs_path, default=default)

    def set_relative_data(
        self,
        path: str,
        value: Any,
        attributes: dict[str, Any] | None = None,
        fired: bool = False,
        reason: Any = None,
    ) -> None:
        """Write ``value`` into ``handler.data`` at ``path``.

        ``path`` is composed via :meth:`BuilderHandler.abs_datapath`
        (same forms as :meth:`get_relative_data`). ``attributes``,
        ``fired`` and ``reason`` are forwarded to ``Bag.set_item`` as
        the corresponding underscore-prefixed parameters. ``reason``
        is polymorphic (DB-D8): the subscriber receives whatever
        object is passed here, unchanged.
        """
        handler = self._resolve_handler()
        abs_path = handler.abs_datapath(self, path)
        handler.data.set_item(
            abs_path,
            value,
            _attributes=attributes,
            _fired=fired,
            _reason=reason,
        )

    def fire_event(
        self,
        path: str,
        value: Any = True,
        attributes: dict[str, Any] | None = None,
        reason: Any = None,
    ) -> None:
        """Write ``value`` to ``path`` marking the event as ``fired``.

        Legacy shortcut for ``set_relative_data(..., fired=True)``
        (DB-D7 point 5). Used when the write is a notification more
        than a data mutation; the ``_fired`` flag flows through the
        Bag subscribe pipeline so downstream consumers can distinguish
        events meant as triggers from ordinary value updates.
        """
        self.set_relative_data(
            path, value, attributes=attributes, fired=True, reason=reason,
        )

    def __getattr__(self, name: str) -> Any:
        """Delegate unknown attribute access to the active builder.

        ``node.div('hello')`` becomes ``builder._command_on_node(...)``
        when the active builder carries a tag named ``div`` in its
        schema. If no grammar tag matches, fall back to a
        ``@struct_method`` dispatched via the owning handler (legacy
        gnrwebstruct parity).
        """
        if name.startswith("_"):
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            )
        builder = self._resolve_builder()
        if builder is None:
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            )
        original_tag = builder._schema_tag_names.get(name.lower())
        if original_tag is None:
            struct = _dispatch_struct_method(self._resolve_handler(), self, name)
            if struct is not None:
                return struct
            builder_method = getattr(type(builder), name, None)
            if getattr(builder_method, "_subbuilder_meta", None) is not None:
                return lambda **attrs: builder_method(builder, self, **attrs)
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            )
        return lambda node_value=None, node_position=None, **attrs: builder._command_on_node(
            self, original_tag,
            node_position=node_position, node_value=node_value, **attrs,
        )

    def __dir__(self) -> list[str]:
        """Expose schema tag names for autocompletion (original case)."""
        base = set(super().__dir__())
        builder = self._resolve_builder()
        if builder is not None:
            base.update(builder._schema_tag_names.values())
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
            1. dunder / private (``_<name>``) → normal lookup (fast path);
               this also covers infrastructure attributes inherited from
               genro_bag (``_node_class``, ``_container_class``, ...).
            2. ``bag_<name>`` → strip prefix and look up the underlying Bag.
            3. ``_builder`` set and ``name`` in its schema → grammar dispatch.
            4. fallback to normal lookup.
        """
        if name.startswith("_"):
            return super().__getattribute__(name)
        if name.startswith("bag_"):
            return super().__getattribute__(name[4:])
        try:
            builder = super().__getattribute__("_builder")
        except AttributeError:
            builder = None
        if builder is not None:
            original_tag = builder._schema_tag_names.get(name.lower())
            if original_tag is not None:
                return builder._bag_call(self, original_tag)
        return super().__getattribute__(name)

    def __getattr__(self, name: str) -> Any:
        """Fallback after the regular attribute lookup fails: dispatch a
        ``@struct_method`` via the owning handler (legacy gnrwebstruct
        parity).
        """
        if name.startswith("_"):
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            )
        struct = _dispatch_struct_method(getattr(self, "_handler", None), self, name)
        if struct is not None:
            return struct
        raise AttributeError(
            f"'{type(self).__name__}' object has no attribute '{name}'"
        )

    def __dir__(self) -> list[str]:
        """Expose schema tag names alongside the regular Bag API (original case)."""
        base = set(super().__dir__())
        builder = getattr(self, "_builder", None)
        if builder is not None:
            base.update(builder._schema_tag_names.values())
        return sorted(base)


class BuilderBagNode(BagNode, _BuilderBagNodeMixin):
    """Level-1 node: BagNode with builder-aware attribute dispatch.

    Level-2 specializations (e.g. ``BuilderSourceNode``, and any
    future ``BuilderDataNode``) inherit from this. See decision 12
    of the contract.
    """

    __slots__ = ("_builder", "_handler")

    # Type annotations for the __slots__ above so type checkers recognize
    # these as members (slots alone are not typed). They hold a builder
    # instance / BuilderHandler, both untyped here.
    _builder: Any
    _handler: Any


class BuilderBag(Bag, _BuilderBagMixin):
    """Level-1 bag: Bag with builder-aware attribute dispatch.

    Level-2 specializations (e.g. ``BuilderSource``, and any future
    ``BuilderData``) inherit from this. See decision 12 of the
    contract. Level-1 bags are not instantiated directly in normal
    flows; the handler uses level-2 subclasses.
    """

    _node_class: type[BagNode] = BuilderBagNode

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
