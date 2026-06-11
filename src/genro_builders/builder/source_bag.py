# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Builder-aware Bag and BagNode — level 1 of the bag/node layering.

Decision 3: ``SourceBag`` and ``SourceBagNode`` are obtained by
combining ``Bag`` with ``_SourceBagMixin`` and ``BagNode`` with
``_SourceBagNodeMixin``. The grammar-aware logic lives in the mixins;
the base classes from ``genro-bag`` stay untouched.

Decision 10: every node carries the ``_builder`` slot — the active
dialect for that node, set at attach time. The owning handler is not a
node slot: it lives on the source root and a node reaches it through the
``handler`` property (``Bag.root``). Immutability is convention-only
during the restart (see ``feedback_lightweight_nodes.md``).

This module defines the bag/node pair (``SourceBag`` /
``SourceBagNode``): a Bag/BagNode carrying the active builder plus
grammar-aware attribute resolution. The builder populates one as
``self.source``.
"""
from __future__ import annotations

import keyword
import warnings
from typing import Any

from genro_bag import Bag, BagNode


def _dispatch_container(builder: Any, target: Any, name: str) -> Any | None:
    """Resolve ``name`` as a ``@container`` on ``builder``.

    Returns a callable bound to ``target`` (bag or node) when the name
    matches a registered container on the builder; ``None`` if no
    match (caller falls through to whatever else it wants to try). The
    container runs with ``self`` = the builder and ``target`` as its
    first positional (the node it was invoked from).
    """
    if builder is None:
        return None
    method_name = builder._containers.get(name.lower())
    if method_name is None:
        return None
    bound = getattr(builder, method_name)
    return lambda *args, **kwargs: bound(target, *args, **kwargs)


class _SourceBagNodeMixin:
    """Builder-aware logic for nodes: schema dispatch via __getattr__.

    The actual slots ``_builder``/``_handler`` are declared on the
    final ``SourceBagNode`` class (BagNode itself uses __slots__,
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

    @property
    def builder(self) -> Any:
        """Active builder for this node, resolved via slot + ancestor walk.

        Public façade of ``_resolve_builder``: returns the node's own
        ``_builder`` slot if set, otherwise the closest ancestor's. The
        renderer-side chain relies on this to dispatch a node to the
        renderer of its owning builder during the walk.
        """
        return self._resolve_builder()

    def _get_meta(self, keys: str) -> Any:
        """Read schema ``_meta`` values carried by this node.

        The element's ``_meta`` dict (declared on the grammar, copied onto
        the node at creation) holds framework instructions for renderers and
        compilers: ``subbuilder``, ``data_element``, ``render_tag``,
        ``render_attributes``, ``compile_*`` … This is the single accessor.

        - one key (``'render_tag'``) → its value, or ``None``;
        - comma-separated keys (``'render_tag,render_attributes'``) → a list
          of values in order, ``None`` where a key is absent.
        """
        meta = self.attr.get("_meta") or {}
        names = [k.strip() for k in keys.split(",")]
        if len(names) == 1:
            return meta.get(names[0])
        return [meta.get(n) for n in names]

    @property
    def handler(self) -> Any:
        """Return the handler that owns this tree.

        The handler is unique for the whole document (host plus any
        sub-builders), so it lives on the source root and is read from
        there via ``Bag.root`` — unlike ``_resolve_builder``, which is a
        single hop because the active builder is local to the node (an
        ``<svg>`` subtree resolves to the SVG builder).
        """
        return self.parent_bag.root._handler

    @property
    def root_builder(self) -> Any:
        """Return the page builder that owns this tree.

        Unlike ``_resolve_builder`` (the local dialect, an ``<svg>``
        subtree resolves to the SVG builder), this is the builder mounted
        on the document — read from the source root via ``Bag.root``. It
        owns the data segment, so data resolution goes through here.
        """
        return self.parent_bag.root._builder

    @property
    def root_builder_name(self) -> Any:
        """Return the mount name of the page builder.

        The builder carries its name from construction; ``add_builder``
        mounts it under that name in the handler's ``_dataroot``, so it
        is the leading segment of an absolute data path for this tree.
        """
        return self.root_builder.name

    def _check_unique_id(self, node_id: Any) -> None:
        """Raise ValueError if ``node_id`` is already taken in the
        document. No-op when ``node_id`` is None.

        Called before adding a child, so the candidate id is checked
        against the existing tree only. Uniqueness is guaranteed by the
        ROOT builder: one node_id namespace per document, sub-builder
        subtrees included (the page-level ``node_by_id`` lookup and the
        symbolic pointers cross dialect boundaries, so the practical
        identity space is the document).

        When no root builder is reachable, the check is a no-op.
        """
        if node_id is None:
            return
        parent = self.parent_bag
        builder = getattr(parent.root, "_builder", None) if parent is not None else None
        if builder is None:
            return
        try:
            builder.node_by_id(node_id)
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
            if self.pointer_type(v) == "^"
        ]
        value = self.value
        if self.pointer_type(value) == "^":
            result.append(("", value))
        return result

    def pointer_type(self, v: Any) -> str | None:
        """Return ``"^"`` (reactive), ``"="`` (passive) or ``None``."""
        if isinstance(v, str) and v[:1] in ("^", "="):
            return v[0]
        return None

    def fixed_attr_items(self) -> Any:
        """Yield ``(name, value)`` for domain attributes, names canonicalized.

        Skips structural meta-attributes and resolves Python-keyword forms
        (``class_`` / legacy ``_class`` -> ``class``).
        """
        meta_attrs = self._resolve_builder()._meta_attrs
        for attrname, v in self.attr.items():
            if attrname in meta_attrs:
                continue
            if attrname.endswith("_") and keyword.iskeyword(attrname[:-1]):
                attrname = attrname[:-1]
            elif attrname.startswith("_") and keyword.iskeyword(attrname[1:]):
                warnings.warn(
                    f"attribute '{attrname}': the leading-underscore form is "
                    f"deprecated, use '{attrname[1:]}_' instead",
                    DeprecationWarning,
                    stacklevel=2,
                )
                attrname = attrname[1:]
            yield attrname, v

    def runtime_to_evaluate(self) -> dict[Any, Any]:
        """Attributes to resolve plus the node value under key ``None``."""
        items: dict[Any, Any] = dict(self.fixed_attr_items())
        items[None] = self.value
        return items

    # ------------------------------------------------------------------
    # Path composition (DAT.2)
    # ------------------------------------------------------------------

    def abs_datapath(self, path: str) -> str:
        """Compose the absolute path for ``path`` relative to this node.

        Pure address composition: returns *where* a datum lives as a
        string, never reads the datastore. Supported syntactic forms:

            ``field``               — absolute on this builder's segment;
                                       the segment name is prepended
            ``^...`` / ``=...``     — pointer mark stripped, recurses.
                                       ``abs_datapath`` is neutral wrt
                                       the prefix; the lazy/eager
                                       distinction (``^`` vs ``=``)
                                       lives in ``runtime_values``
                                       and in the pointer-map registry
            ``volume:field``        — ``volume`` is the leading segment
                                       instead of this builder's own (so
                                       ``_:x`` reaches the common segment)
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
        if self.pointer_type(path):
            path = path[1:]

        attr: str | None = None
        if "?" in path:
            path, attr = path.split("?", 1)

        volume = self.root_builder_name
        if ":" in path and not path.startswith("."):
            volume, path = path.split(":", 1)
            return self._compose_abs_path(volume, path, attr)

        if path.startswith("#"):
            return self._resolve_symbolic_datapath(path, raw)

        if path.startswith("."):
            path = self._compose_relative_datapath(path, raw)
        return self._compose_abs_path(volume, path, attr)

    def _compose_abs_path(
        self, volume: str, path: str, attr: str | None,
    ) -> str:
        """Compose ``volume.path`` into an absolute datastore path.

        ``path`` is collapsed (``#parent`` segments resolved) before the
        leading ``volume`` segment is prepended, so the segment is never
        cancelled; ``?attr`` is re-attached at the tail when present.
        """
        path = self._collapse_parent_datapath(path, path)
        base = f"{volume}.{path}"
        return f"{base}?{attr}" if attr else base

    def _compose_relative_datapath(self, path: str, raw: str) -> str:
        """Resolve a relative path by walking ancestors.

        Chains ``attr["datapath"]`` of ancestors (starting from this
        node) in front of ``path`` until the result no longer starts
        with ``.``. Stops at the first ancestor whose ``datapath`` is
        absolute. Raises ``ValueError`` if the chain ends while
        ``path`` is still relative.

        A bare ``"."`` denotes the current datapath itself (no child
        segment) — used by ``.?attr`` paths that read an attribute of the
        datapath node. It resolves to the datapath alone, without a dangling
        trailing dot (so ``.?b`` -> ``triangolo?b``, not ``triangolo.?b``).
        """
        # ``current`` typed as Any: the mixin is combined with BagNode
        # at runtime to form SourceBagNode, but pyright analyses the
        # mixin in isolation and can't see the eventual concrete shape.
        current: Any = self
        while current is not None and path.startswith("."):
            dp = current.attr.get("datapath")
            if dp is not None:
                path = dp if path == "." else dp + path
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
            builder = self._resolve_builder()
            if builder is None:
                raise KeyError(
                    f"#<id>: cannot resolve {raw!r} on a node without builder"
                )
            anchor = builder.node_by_id(symbol)
        rel = f".{relpath}" if relpath else "."
        result: str = anchor.abs_datapath(rel)
        return result

    # ------------------------------------------------------------------
    # Runtime evaluation (DAT.2, slice0)
    # ------------------------------------------------------------------

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
        """Read the datastore at ``path`` resolved relative to this node.

        ``path`` is composed via :meth:`abs_datapath` into an absolute
        path on ``handler.data`` (the segmented ``_dataroot``); it accepts
        the same syntactic forms (absolute, relative ``.x``, ``#FORM``,
        ``#ANCHOR``, ``#<node_id>``, ``volume:rest``, with or without the
        ``^``/``=`` prefix).

        When ``autocreate=True``, a ``None`` value at ``path`` (missing or
        explicitly ``None``) is seeded with ``default`` before the read —
        the two cases are intentionally not distinguished (DBS-D1).
        """
        data = self.handler.data
        abs_path = self.abs_datapath(path)
        if autocreate and data.get_item(abs_path) is None:
            data.set_item(abs_path, default)
        return data.get_item(abs_path, default=default)

    def set_relative_data(
        self,
        path: str,
        value: Any,
        attributes: dict[str, Any] | None = None,
        fired: bool = False,
        reason: Any = None,
    ) -> None:
        """Write ``value`` into the datastore at ``path``.

        ``path`` is composed via :meth:`abs_datapath` into an absolute
        path on ``handler.data`` (same forms as :meth:`get_relative_data`).
        ``attributes``/``fired``/``reason`` are forwarded to
        ``Bag.set_item`` as the underscore-prefixed parameters. ``reason``
        is polymorphic (DB-D8): the subscriber receives whatever object is
        passed. Legacy parity (``gnrdomsource.js`` ``reason == null ?
        true``): an omitted ``reason`` becomes ``True``, so a plain write
        declares itself the origin; pass ``reason=False`` (``PUT``) to
        override.
        """
        handler = self.handler
        abs_path = self.abs_datapath(path)
        handler.data.set_item(
            abs_path,
            value,
            _attributes=attributes,
            _fired=fired,
            _reason=True if reason is None else reason,
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

    # ------------------------------------------------------------------
    # Reactive DSL macros (uppercase by design) — legacy gnrlang.js parity
    # ------------------------------------------------------------------
    #
    # SET/GET/PUT/FIRE are the reactive write/read vocabulary a data-element
    # func uses on its ``node`` (e.g. ``node.SET(".total", x)``). They are thin
    # aliases of set_relative_data/get_relative_data with the reason/fired
    # constants pre-wired. The UPPERCASE is deliberate (not a style slip): the
    # node carries dozens of lowercase methods, and these few must stand out as
    # the DSL operations that drive the reactive cascade — continuity with the
    # legacy JS where developers recognise ``SET .x = ...`` / ``FIRE``.

    def SET(self, path: str, value: Any) -> None:
        """Reactive write: ``set_relative_data`` with the default reason.

        The omitted reason becomes ``True`` (the write is its own origin),
        per :meth:`set_relative_data` legacy parity.
        """
        self.set_relative_data(path, value)

    def GET(self, path: str) -> Any:
        """Reactive read: ``get_relative_data(path)``."""
        return self.get_relative_data(path)

    def PUT(self, path: str, value: Any) -> None:
        """Quiet write: ``set_relative_data`` with ``reason=False``.

        Unlike :meth:`SET`, ``PUT`` declares itself NOT the origin of the
        change (legacy ``reason=False``), so an originating widget would not
        bounce back on its own write.
        """
        self.set_relative_data(path, value, reason=False)

    def FIRE(self, path: str, value: Any = True) -> None:
        """Event write: ``set_relative_data`` with ``fired=True``.

        Value defaults to ``True``; the ``_fired`` flag flows through the bag
        subscribe pipeline so downstream consumers can tell triggers from
        ordinary value updates.
        """
        self.set_relative_data(path, value, fired=True)

    def __getattr__(self, name: str) -> Any:
        """Delegate unknown attribute access to the active builder.

        ``node.div('hello')`` becomes ``builder._command_on_node(...)``
        when the active builder carries a tag named ``div`` in its
        schema. The grammar semantics (data-element field mapping,
        ``node_id`` uniqueness, sub-builder switch) live in the shared
        wrapper both entry points converge on — this is pure routing.
        If no grammar tag matches, fall back to a ``@container``
        dispatched via the active builder (legacy gnrwebstruct parity).
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
            struct = _dispatch_container(builder, self, name)
            if struct is not None:
                return struct
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            )

        def element_call(*args: Any, node_position: Any = None, **attrs: Any) -> Any:
            return builder._command_on_node(
                self, original_tag, *args,
                node_position=node_position, **attrs,
            )

        return element_call

    def __dir__(self) -> list[str]:
        """Expose schema tag names for autocompletion (original case)."""
        base = set(super().__dir__())
        builder = self._resolve_builder()
        if builder is not None:
            base.update(builder._schema_tag_names.values())
        return sorted(base)


class _SourceBagMixin:
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
        ``@container`` via the active builder (legacy gnrwebstruct
        parity).
        """
        if name.startswith("_"):
            raise AttributeError(
                f"'{type(self).__name__}' object has no attribute '{name}'"
            )
        struct = _dispatch_container(getattr(self, "_builder", None), self, name)
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


class SourceBagNode(BagNode, _SourceBagNodeMixin):
    """BagNode with builder-aware attribute dispatch."""

    __slots__ = ("_builder", "_target_id")

    # Type annotations for the __slots__ above so type checkers recognize
    # them as members (slots alone are not typed). ``_builder`` holds the
    # active builder instance; ``_target_id`` the per-document serial
    # (assigned lazily by ``BuilderBase.target_id``, read with getattr —
    # an unset slot raises and ``__getattr__`` re-raises for ``_`` names).
    _builder: Any
    _target_id: str


class SourceBag(Bag, _SourceBagMixin):
    """Bag with builder-aware attribute dispatch.

    The handler instantiates one as ``self.source``; ``new_root``
    returns a detached one for offline subtree building.
    """

    _node_class: type[BagNode] = SourceBagNode

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
            builder: BuilderBase instance whose schema drives attribute
                dispatch on this bag (and on nodes attached to it).
            handler: BuilderHandler that owns the tree this bag belongs to.
        """
        super().__init__(source=source)
        self._builder = builder
        self._handler = handler
