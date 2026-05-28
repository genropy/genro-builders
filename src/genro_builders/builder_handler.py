# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BuilderHandler — engine that drives a single Builder (decisions 4, 5, 9).

The handler owns:
    - one ``builder`` instance (decision 4: handler manages its builder);
    - two wrapper bags, ``_sourceroot`` and ``_dataroot``, each holding
      the live payload under the key ``"main"``:

          _sourceroot["main"] = BuilderSource(...)   # alias: self.source
          _dataroot  ["main"] = Bag()                # alias: self.data

      Wrapping the payload under a stable root lets the subscription
      live on the wrapper (not on the payload), so it survives hot-swap
      of the payload (mirrors the legacy JS ``gnrdomsource.js`` pattern);
    - the dict ``mode -> target`` of render targets (decision 6).

Reactive hooks:
    Subclasses react to mutations by overriding the no-op hooks
    :meth:`on_source_change` and :meth:`on_data_change`. The handler
    subscribes to both wrappers in ``__init__`` and dispatches every
    insert/update/delete through the internal callbacks
    :meth:`_on_source_event` / :meth:`_on_data_event`, which normalize
    the event code to ``"ins"`` / ``"upd"`` / ``"del"`` and split the
    update subtype into ``evt_detail`` (e.g. ``"value"`` for the genro_bag
    ``"upd_value"`` code).

Lifecycle (decision 5):
    handler = MyHandler()
    handler.create()    # main(source) -> populate self.source
    handler.render()    # dispatch to the renderer bound to the
                        # default mode, using its registered target.

Subclasses (typically ``HtmlBuilderHandler``, etc.) set
``builder_class`` and override ``main(self, root)``.
"""
from __future__ import annotations

from typing import Any

from genro_bag import Bag, BagNode

from .builder import BagBuilderBase
from .builder_bag import BuilderBagNode
from .source_bag import BuilderSource


class BuilderHandler:
    """Engine that drives one builder through the create/render lifecycle.

    Holds two wrapper bags (``_sourceroot`` and ``_dataroot``), each with
    the active payload under the key ``"main"``, and exposes the payloads
    as :attr:`source` and :attr:`data`. Subscribes both wrappers in
    ``__init__`` and routes every event to the public override points
    :meth:`on_source_change` / :meth:`on_data_change`. See the module
    docstring for the full picture.
    """

    builder_class: type | None = None
    _struct_methods: dict[str, str]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Collect @struct_method declarations into ``cls._struct_methods``.

        Legacy parity (gnrwebstruct.base.struct_method):
            - dispatch name = explicit ``@struct_method('alias')`` if given,
              else attr name with prefix-before-first-underscore stripped,
              else attr name itself;
            - dispatch lookup is case-insensitive (key stored lowercase);
            - cross-MRO collisions: same dispatch name + same attr name
              (subclass override) is allowed; same dispatch name + different
              attr name raises ValueError.
        """
        super().__init_subclass__(**kwargs)
        merged: dict[str, str] = {}
        for klass in reversed(cls.__mro__):
            parent_map = klass.__dict__.get("_struct_methods")
            if parent_map:
                merged.update(parent_map)
        for attr_name, obj in cls.__dict__.items():
            decorator = getattr(obj, "_decorator", None)
            if decorator is None:
                continue
            if not decorator.get("struct_method"):
                raise ValueError(
                    f"BuilderHandler subclass {cls.__name__} has decorated "
                    f"method '{attr_name}' that is not @struct_method",
                )
            explicit = decorator.get("name")
            if explicit is not None:
                dispatch_name = explicit
            elif "_" in attr_name:
                dispatch_name = attr_name.split("_", 1)[1]
            else:
                dispatch_name = attr_name
            key = dispatch_name.lower()
            existing = merged.get(key)
            if existing is not None and existing != attr_name:
                raise ValueError(
                    f"@struct_method '{dispatch_name}' is already tied to "
                    f"implementation method '{existing}' (cannot rebind to "
                    f"'{attr_name}')"
                )
            merged[key] = attr_name
        cls._struct_methods = merged

    def __init__(self) -> None:
        if self.builder_class is None:
            raise TypeError(
                f"{type(self).__name__} must declare a builder_class "
                "(decision 9: handler subclasses bind a specific builder).",
            )
        self.builder = self.builder_class()
        self._sourceroot: Bag = Bag()
        self._dataroot: Bag = Bag()
        self._sourceroot["main"] = BuilderSource(builder=self.builder, handler=self)
        self._dataroot["main"] = Bag()
        self.source: BuilderSource = self._sourceroot["main"]
        self.data: Bag = self._dataroot["main"]
        # HND.2 — wrapper-root strutturale: backref acceso sempre, in modo
        # esplicito. Serve a abs_datapath e alla risalita ancestor in genere.
        # Indipendente dalle subscribe (che oggi lo attiverebbero comunque
        # come side-effect, ma il loro scopo è la reattività push, non la
        # struttura).
        self._sourceroot.set_backref()
        self._dataroot.set_backref()
        self.renderers: dict[str, dict[str, Any]] = {}
        self._default_render_mode: str | None = None
        self._sourceroot.subscribe(
            "builder_handler_source",
            insert=self._on_source_event,
            update=self._on_source_event,
            delete=self._on_source_event,
        )
        self._dataroot.subscribe(
            "builder_handler_data",
            insert=self._on_data_event,
            update=self._on_data_event,
            delete=self._on_data_event,
        )

    def _ensure_mode(self, mode: str) -> dict[str, Any]:
        """Return the ``self.renderers[mode]`` entry, creating it lazily.

        Each entry holds ``{"target": ..., "instance": RendererBase}``.
        The renderer class is read from the builder's registry the first
        time the mode is touched (either by ``set_render_target`` or by
        ``render``).
        """
        entry = self.renderers.get(mode)
        if entry is None:
            renderer_cls = self.builder._renderers[mode]
            entry = {"target": None, "instance": renderer_cls(self)}
            self.renderers[mode] = entry
        return entry

    # ------------------------------------------------------------------
    # Lifecycle (decision 5)
    # ------------------------------------------------------------------

    def create(self) -> None:
        """Populate the source bag by invoking ``main(self.source)``."""
        self.main(self.source)

    def render(
        self,
        target: Any = None,
        mode: str | None = None,
        **kwargs: Any,
    ) -> Any:
        """Render the source via the renderer bound to ``mode``.

        Argument ``target`` semantics (decision 6 v0.4.0):

        - ``False`` → forces return-as-string, ignores any registered
          target for the chosen mode;
        - any other falsy value (``None``, ``""``, ``0``) → falls back
          to the target registered under ``mode`` (see
          ``set_render_target``);
        - truthy value → used directly as the target for this call.

        ``mode`` resolution:

        - explicit ``mode`` argument wins;
        - otherwise the handler's ``_default_render_mode`` (set via
          ``set_render_target(..., default=True)``);
        - otherwise the builder's ``_default_render_mode``.

        The renderer corresponding to ``mode`` is looked up in the
        builder's ``_renderers`` registry and instantiated on the fly.
        """
        effective_mode = (
            mode
            or self._default_render_mode
            or self.builder._default_render_mode
        )
        entry = self._ensure_mode(effective_mode)
        if target is False:
            effective_target = None
        elif not target:
            effective_target = entry["target"]
        else:
            effective_target = target
        return entry["instance"].render(
            self.source,
            mode=effective_mode,
            render_target=effective_target,
            **kwargs,
        )

    def set_render_target(
        self,
        mode: str,
        target: Any,
        default: bool = False,
    ) -> None:
        """Register a render target for ``mode``.

        Overrides any previous registration under the same mode. When
        ``default=True`` the mode also becomes the handler's default
        for plain ``self.render()`` calls.
        """
        self._ensure_mode(mode)["target"] = target
        if default:
            self._default_render_mode = mode

    def __getattr__(self, name: str) -> Any:
        """Auto-generated ``render_<mode>`` shortcuts.

        ``handler.render_xml('out.xml')`` is equivalent to
        ``handler.render(target='out.xml', mode='xml')``. The shortcut
        is generated only when the mode exists in the builder's
        renderer registry; otherwise the lookup falls through to the
        normal ``AttributeError``.
        """
        if name.startswith("render_"):
            mode = name[len("render_"):]
            registry = getattr(self.builder, "_renderers", None)
            if registry is not None and mode in registry:
                def shortcut(target: Any = None, **kwargs: Any) -> Any:
                    return self.render(target=target, mode=mode, **kwargs)
                return shortcut
        raise AttributeError(
            f"{type(self).__name__!r} object has no attribute {name!r}",
        )

    # ------------------------------------------------------------------
    # Renderer property (decision 8)
    # ------------------------------------------------------------------

    @property
    def renderer(self) -> Any:
        """Dialect renderer for the builder's default mode.

        Available for inspection (``handler.renderer._STYLE_ROOTS``,
        etc.) or for explicit calls when the shortcut
        ``handler.render(...)`` is too narrow. The instance is created
        on first access and kept in ``self.renderers``.
        """
        return self._ensure_mode(self.builder._default_render_mode)["instance"]

    # ------------------------------------------------------------------
    # Sub-builder access (decision 2)
    # ------------------------------------------------------------------

    def get_subbuilder(self, name: str) -> Any:
        """Return a sub-builder instance by canonical name.

        Looks up the class in the global registry via
        :meth:`BagBuilderBase.get_builder_class` and instantiates it.
        """
        return BagBuilderBase.get_builder_class(name)()

    def renderer_for(self, builder: Any) -> Any:
        """Return the renderer instance bound to ``builder``.

        For the primary builder this is ``self.renderer``. For a
        sub-builder (a different dialect attached to a subtree), the
        renderer class is read from the sub-builder's renderer registry
        (default mode) and instantiated on the spot. The sub-renderer
        carries an explicit ``builder`` reference so polymorphic
        dispatch via ``node._builder`` can identify it correctly.
        """
        if builder is self.builder:
            return self.renderer
        mode = builder._default_render_mode
        return builder._renderers[mode](self, builder)

    # ------------------------------------------------------------------
    # Wrapper-root subscriptions (decision 11 + HWR refactor)
    # ------------------------------------------------------------------

    def _on_source_event(self, node: BuilderBagNode, evt: str, **kw: Any) -> None:
        """Internal dispatcher for events on ``_sourceroot``.

        Normalizes the raw bag event and forwards it to
        :meth:`on_source_change`.
        """
        if evt == "ins":
            self.on_source_change(node, "ins", evt_detail=None, **kw)
        elif evt == "del":
            self.on_source_change(node, "del", evt_detail=None, **kw)
        else:
            detail = evt[4:] if evt.startswith("upd_") else evt
            self.on_source_change(node, "upd", evt_detail=detail, **kw)

    def _on_data_event(self, node: BuilderBagNode, evt: str, **kw: Any) -> None:
        """Internal dispatcher for events on ``_dataroot``.

        Forwards a normalized event to :meth:`on_data_change`.
        """
        if evt == "ins":
            self.on_data_change(node, "ins", evt_detail=None, **kw)
        elif evt == "del":
            self.on_data_change(node, "del", evt_detail=None, **kw)
        else:
            detail = evt[4:] if evt.startswith("upd_") else evt
            self.on_data_change(node, "upd", evt_detail=detail, **kw)

    def node_by_id(self, node_id: str) -> BuilderBagNode:
        """Return the source node carrying ``node_id``.

        Walk-based lookup over the source tree. Raises ``KeyError`` if
        no node carries the requested id.
        """
        node = self.source.get_node_by_attr("node_id", node_id)
        if node is None:
            raise KeyError(node_id)
        return node

    def abs_datapath(self, node: BuilderBagNode, path: str) -> str:
        """Compose the absolute path for ``path`` relative to ``node``.

        Pure address composition: returns *where* a datum lives as a
        string, never reads the datastore. Supported syntactic forms:

            ``field``               — absolute, returned as-is
            ``^...``                — pointer mark stripped, recurses
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
        if path.startswith("^"):
            path = path[1:]

        if path.startswith("#"):
            return self._resolve_symbolic(node, path, raw)

        volume: str | None = None
        if ":" in path and not path.startswith("."):
            volume, path = path.split(":", 1)

        attr: str | None = None
        if "?" in path:
            path, attr = path.split("?", 1)

        if path.startswith("."):
            path = self._compose_relative(node, path, raw)

        composed = path
        if volume is not None:
            composed = f"{volume}:{composed}"
        if attr is not None:
            composed = f"{composed}?{attr}"
        if "#parent" in composed:
            composed = self._collapse_parent(composed, raw)
        return composed

    def _compose_relative(
        self,
        node: BuilderBagNode,
        path: str,
        raw: str,
    ) -> str:
        """Resolve a relative path by walking ancestors.

        Chains ``attr["datapath"]`` of ancestors (starting from ``node``)
        in front of ``path`` until the result no longer starts with
        ``.``. Stops at the first ancestor whose ``datapath`` is
        absolute. Raises ``ValueError`` if the chain ends while ``path``
        is still relative.
        """
        current: BagNode | None = node
        while current is not None and path.startswith("."):
            dp = current.attr.get("datapath")
            if dp is not None:
                path = dp + path
            current = current.parent_node
        if path.startswith("."):
            raise ValueError(f"unresolved relative datapath: {raw!r}")
        return path

    def _collapse_parent(self, path: str, raw: str) -> str:
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

    def _resolve_symbolic(
        self,
        node: BuilderBagNode,
        path: str,
        raw: str,
    ) -> str:
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
            anchor = self._find_marked_ancestor(node, form=True, anchor=False, raw=raw)
        elif symbol == "ANCHOR":
            anchor = self._find_marked_ancestor(node, form=False, anchor=True, raw=raw)
        else:
            anchor = self.node_by_id(symbol)
        rel = f".{relpath}" if relpath else "."
        return self.abs_datapath(anchor, rel)

    def _find_marked_ancestor(
        self,
        node: BuilderBagNode,
        *,
        form: bool,
        anchor: bool,
        raw: str,
    ) -> BuilderBagNode:
        """Walk ancestors looking for a node carrying the requested marker.

        Markers:
            ``form=True``   — ``formId`` set OR ``form=True`` in attrs;
            ``anchor=True`` — ``_anchor`` present in attrs.

        The walk starts from ``node`` itself. Raises ``KeyError`` if no
        ancestor satisfies the marker.
        """
        current: BagNode | None = node
        while current is not None:
            attrs = current.attr
            if form and (attrs.get("formId") is not None or attrs.get("form") is True):
                return current
            if anchor and "_anchor" in attrs:
                return current
            current = current.parent_node
        marker = "FORM" if form else "ANCHOR"
        raise KeyError(f"#{marker}: no marked ancestor found for {raw!r}")

    # ------------------------------------------------------------------
    # Reactive hooks (subtask handler_wrapper_root, P2)
    # ------------------------------------------------------------------

    def on_source_change(
        self,
        node: BuilderBagNode,
        evt: str,
        evt_detail: str | None = None,
        **kw: Any,
    ) -> None:
        """Override point. Called for every insert/update/delete on source.

        ``evt`` is the normalized 3-letter event code: ``"ins"``, ``"upd"``,
        ``"del"``. ``evt_detail`` carries the update subtype when ``evt ==
        "upd"`` (e.g. ``"value"``, ``"attrs"``, or any custom string
        emitted by the mutator); it is ``None`` for inserts and deletes.
        Default implementation is a no-op; subclasses override to react to
        source mutations.
        """

    def on_data_change(
        self,
        node: BuilderBagNode,
        evt: str,
        evt_detail: str | None = None,
        **kw: Any,
    ) -> None:
        """Override point. Called for every insert/update/delete on data.

        Same protocol as :meth:`on_source_change` but for the ``data``
        wrapper. Default implementation is a no-op.
        """

    # ------------------------------------------------------------------
    # User hook
    # ------------------------------------------------------------------

    def main(self, root: BuilderSource) -> None:
        """Override in subclass to populate the source bag."""
        raise NotImplementedError(
            f"{type(self).__name__}.main(root) must be implemented by the subclass",
        )
