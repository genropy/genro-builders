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

import re
from typing import Any

from genro_bag import Bag, BagNode

# Template token used by ``runtime_values`` to spot ``${name}``
# placeholders in attribute values and node values (DB-D11).
_TEMPLATE_RE = re.compile(r"\$\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


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

    # ------------------------------------------------------------------
    # Path composition (DAT.2) — moved here from BuilderHandler
    # ------------------------------------------------------------------

    def abs_datapath(self, path: str) -> str:
        """Compose the absolute path for ``path`` relative to this node.

        Pure address composition: returns *where* a datum lives as a
        string, never reads the datastore. Supported syntactic forms:

            ``field``               — absolute, returned as-is
            ``^...`` / ``=...``     — pointer mark stripped, recurses.
                                       ``abs_datapath`` is neutral wrt
                                       the prefix; the lazy/eager
                                       distinction (``^`` vs ``=``)
                                       lives in ``runtime_values``
                                       and in the pointer-map registry
            ``volume:field``        — absolute in another builder; the
                                       ``volume:`` prefix is preserved,
                                       routing happens at read time
            ``field?attr``          — ``?attr`` is preserved at the tail
            ``.field`` / ``.x``     — relative: walk ancestors and
                                       chain their ``datapath`` attribute
                                       until the result is absolute;
                                       ``ValueError`` if the chain ends
                                       without an absolute anchor
            ``a.#parent.b``         — ``#parent`` segments cancel the
                                       preceding segment (filesystem
                                       ``..`` equivalent); ``ValueError``
                                       if it has nothing left to cancel
            ``#FORM.x``             — relative to the nearest ancestor
                                       marked with ``formId`` set or
                                       ``form=True``; ``KeyError`` if no
                                       such ancestor
            ``#ANCHOR.x``           — relative to the nearest ancestor
                                       with attr ``_anchor`` present;
                                       ``KeyError`` otherwise
            ``#<node_id>.x``        — relative to the node carrying that
                                       ``node_id`` (any other ``#xxx``
                                       falls in here); ``KeyError`` if
                                       no node carries that id
        """
        raw = path
        if path and path[0] in ("^", "="):
            path = path[1:]

        if path.startswith("#"):
            return self._resolve_symbolic_datapath(path, raw)

        volume: str | None = None
        if ":" in path and not path.startswith("."):
            volume, path = path.split(":", 1)

        attr: str | None = None
        if "?" in path:
            path, attr = path.split("?", 1)

        if path.startswith("."):
            path = self._compose_relative_datapath(path, raw)

        composed = path
        if volume is not None:
            composed = f"{volume}:{composed}"
        if attr is not None:
            composed = f"{composed}?{attr}"
        if "#parent" in composed:
            composed = self._collapse_parent_datapath(composed, raw)
        return composed

    def _compose_relative_datapath(self, path: str, raw: str) -> str:
        """Resolve a relative path by walking ancestors.

        Chains ``attr["datapath"]`` of ancestors (starting from this
        node) in front of ``path`` until the result no longer starts
        with ``.``. Stops at the first ancestor whose ``datapath`` is
        absolute. Raises ``ValueError`` if the chain ends while
        ``path`` is still relative.
        """
        # ``current`` typed as Any: the mixin is combined with BagNode
        # at runtime to form BuilderBagNode, but pyright analyses the
        # mixin in isolation and can't see the eventual concrete shape.
        current: Any = self
        while current is not None and path.startswith("."):
            dp = current.attr.get("datapath")
            if dp is not None:
                path = dp + path
            current = current.parent_node
        if path.startswith("."):
            raise ValueError(f"unresolved relative datapath: {raw!r}")
        return path

    def _collapse_parent_datapath(self, path: str, raw: str) -> str:
        """Collapse ``#parent`` segments in a composed path.

        Path-level rewrite: each ``#parent`` segment cancels the segment
        immediately before it (``a.b.#parent.c`` -> ``a.c``). Raises
        ``ValueError`` when ``#parent`` has no segment left to cancel,
        rather than silently dropping it.
        """
        out: list[str] = []
        for segment in path.split("."):
            if segment == "#parent":
                if not out:
                    raise ValueError(
                        f"#parent has no segment to cancel: {raw!r}"
                    )
                out.pop()
            else:
                out.append(segment)
        return ".".join(out)

    def _resolve_symbolic_datapath(self, path: str, raw: str) -> str:
        """Resolve a ``#SYMBOL[.relpath]`` path.

        Dispatch (path starts with ``#``):
            ``#FORM``       — nearest ancestor with attr ``formId`` set
                              OR ``form=True``;
            ``#ANCHOR``     — nearest ancestor with attr ``_anchor``
                              present (any value);
            ``#<id>``       — node carrying that ``node_id`` (any other
                              ``#xxx`` falls in here).

        The matching ancestor / node is then used as starting point for
        a relative resolution of ``relpath`` via ``abs_datapath``, so
        the ancestor's own ``datapath`` chain is consulted normally.
        """
        symbol, _, relpath = path[1:].partition(".")
        if symbol == "FORM":
            anchor = self._find_marked_datapath_ancestor(
                form=True, anchor=False, raw=raw,
            )
        elif symbol == "ANCHOR":
            anchor = self._find_marked_datapath_ancestor(
                form=False, anchor=True, raw=raw,
            )
        else:
            handler = self._resolve_handler()
            if handler is None:
                raise KeyError(
                    f"#<id>: cannot resolve {raw!r} on a node without handler"
                )
            anchor = handler.node_by_id(symbol)
        rel = f".{relpath}" if relpath else "."
        result: str = anchor.abs_datapath(rel)
        return result

    # ------------------------------------------------------------------
    # Runtime evaluation (DAT.2, slice0) — moved here from BuilderHandler
    # ------------------------------------------------------------------

    def runtime_values(self) -> tuple[Any, dict[str, Any]]:
        """Resolve pointers and templates carried by this node.

        Returns ``(runtime_value, runtime_attrs)``. Two-phase pipeline
        (DB-D5, DB-D11):

        Phase 1 — pointer resolution. Any string starting with ``^`` or
        ``=`` (on ``self.value`` or on ``self.attr[name]``) is composed
        through :meth:`abs_datapath` and looked up in ``handler.data``
        via ``Bag.get_item``; non-pointer values pass through verbatim.

        Phase 2 — template expansion. After phase 1, any string still
        carrying ``${name}`` placeholders is expanded against the
        resolved attrs from phase 1: ``${name}`` becomes
        ``str(resolved[name])``, or the empty string ``""`` when
        ``resolved[name]`` is ``None`` (DB-D11.6). ``KeyError`` is
        raised if ``name`` is not in ``resolved``.

        DB-D11 forbids cascade: an attribute is either a pointer OR a
        template OR a literal — never two at once. Phase 2 only acts on
        strings that did NOT match the pointer prefix in phase 1, so
        the invariant holds by construction.

        Errors raised by :meth:`abs_datapath`
        (``ValueError`` / ``KeyError``) propagate unchanged. Absent
        data on a valid path resolves to ``None`` (DB-D10: no internal
        try/except; the caller decides whether ``None`` is meaningful).
        """
        handler = self._resolve_handler()
        resolved: dict[str, Any] = {}
        for attrname, v in self.attr.items():
            if isinstance(v, str) and v and v[0] in ("^", "="):
                path = self.abs_datapath(v)
                resolved[attrname] = handler.data.get_item(path)
            else:
                resolved[attrname] = v

        value = self.value
        if isinstance(value, str) and value and value[0] in ("^", "="):
            runtime_value: Any = handler.data.get_item(
                self.abs_datapath(value),
            )
        else:
            runtime_value = value

        def _expand(s: str) -> str:
            def repl(m: re.Match[str]) -> str:
                name = m.group(1)
                val = resolved[name]
                return "" if val is None else str(val)
            return _TEMPLATE_RE.sub(repl, s)

        for attrname, v in list(resolved.items()):
            if isinstance(v, str) and "${" in v:
                resolved[attrname] = _expand(v)

        if isinstance(runtime_value, str) and "${" in runtime_value:
            runtime_value = _expand(runtime_value)

        return runtime_value, resolved

    def _find_marked_datapath_ancestor(
        self,
        *,
        form: bool,
        anchor: bool,
        raw: str,
    ) -> Any:
        """Walk ancestors looking for a node carrying the requested marker.

        Markers:
            ``form=True``   — ``formId`` set OR ``form=True`` in attrs;
            ``anchor=True`` — ``_anchor`` present in attrs.

        The walk starts from this node itself. Raises ``KeyError`` if
        no ancestor satisfies the marker.
        """
        # ``current`` typed as Any for the same reason explained in
        # _compose_relative_datapath: mixin analysed in isolation.
        current: Any = self
        while current is not None:
            attrs = current.attr
            if form and (attrs.get("formId") is not None or attrs.get("form") is True):
                return current
            if anchor and "_anchor" in attrs:
                return current
            current = current.parent_node
        marker = "FORM" if form else "ANCHOR"
        raise KeyError(f"#{marker}: no marked ancestor found for {raw!r}")

    def get_relative_data(
        self,
        path: str,
        autocreate: bool = False,
        default: Any = None,
    ) -> Any:
        """Read ``handler.data`` at ``path`` resolved relative to this node.

        ``path`` is composed via :meth:`abs_datapath`, so
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
        abs_path = self.abs_datapath(path)
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

        ``path`` is composed via :meth:`abs_datapath`
        (same forms as :meth:`get_relative_data`). ``attributes``,
        ``fired`` and ``reason`` are forwarded to ``Bag.set_item`` as
        the corresponding underscore-prefixed parameters. ``reason``
        is polymorphic (DB-D8): the subscriber receives whatever
        object is passed here, unchanged.
        """
        handler = self._resolve_handler()
        abs_path = self.abs_datapath(path)
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
