# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""BuilderHandler — engine that drives a single Builder (decisions 4, 5, 9).

The handler owns:
    - one ``builder`` instance (decision 4: handler manages its builder);
    - two wrapper bags, ``_sourceroot`` and ``_dataroot``, each holding
      the live payload under the key ``"main"``:

          _sourceroot["main"] = SourceBag(...)      # alias: self.source
          _dataroot  ["main"] = Bag()                # alias: self.data

      Wrapping the payload under a stable root lets the subscription
      live on the wrapper (not on the payload), so it survives hot-swap
      of the payload (mirrors the legacy JS ``gnrdomsource.js`` pattern);
    - the dict ``mode -> target`` of render targets (decision 6).

Reactive hooks:
    Subclasses react to mutations by overriding the no-op hooks
    :meth:`on_source_change` and :meth:`on_data_change`. The handler
    subscribes to both wrappers in ``create()`` (after the construction
    phase, so initial structural inserts in ``main()`` do not fire
    premature reactive events) and dispatches every
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

import inspect
import threading
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from typing import Any

from genro_bag import Bag

from .source_bag import SourceBag, SourceBagNode


class BuilderHandler:
    """Engine that drives one builder through the create/render lifecycle.

    Holds two wrapper bags (``_sourceroot`` and ``_dataroot``), each with
    the active payload under the key ``"main"``, and exposes the payloads
    as :attr:`source` and :attr:`data`. ``create()`` subscribes both
    wrappers (not ``__init__``, so the inserts from ``main`` do not
    dispatch) and routes every event to the public override points
    :meth:`on_source_change` / :meth:`on_data_change`. See the module
    docstring for the full picture.
    """

    builder_class: type | None = None

    def __init__(self, application: Any = None) -> None:
        if self.builder_class is None:
            raise TypeError(
                f"{type(self).__name__} must declare a builder_class "
                "(decision 9: handler subclasses bind a specific builder).",
            )
        # The Application that owns this handler (dual relationship: the
        # app passes itself in). ``None`` means the handler is standalone —
        # sync/pull only. A handler is reactive precisely because it has an
        # application; reactivity is the relationship, not an internal flag.
        self.application = application
        self.builder = self.builder_class()
        self._sourceroot: SourceBag = SourceBag(
            builder=self.builder, handler=self,
        )
        self._dataroot: SourceBag = SourceBag(
            builder=self.builder, handler=self,
        )
        self._sourceroot["main"] = SourceBag(builder=self.builder, handler=self)
        self._dataroot["main"] = Bag()
        self.source: SourceBag = self._sourceroot["main"]
        self.data: Bag = self._dataroot["main"]
        # HND.2 — wrapper-root strutturale: backref acceso sempre, in modo
        # esplicito. Serve a abs_datapath e alla risalita ancestor in genere.
        # Indipendente dalle subscribe (che oggi lo attiverebbero comunque
        # come side-effect, ma il loro scopo è la reattività push, non la
        # struttura).
        self._sourceroot.set_backref()
        self._dataroot.set_backref()
        self.renderers: dict[str, Any] = {}
        self._default_targets: dict[str, Any] = {}
        self._default_render_mode: str | None = None
        # DAT.2 — mappa delle dipendenze pointer. Chiave = path assoluto;
        # valore = dict ``{id(node): node}``. Popolata alla lettura
        # (``_register_path`` durante il render); ripulita dei nodi spariti
        # da ``_unregister_pointer`` su mutazione di source.
        self.pointer_map: dict[str, dict[int, SourceBagNode]] = {}
        # RX livello 0 — flag di abilitazione reattività: acceso dal PRIMO
        # render (non da create()). Segna che l'avviamento è finito: la
        # pointer_map è popolata (lettura a render time) e live() è permesso.
        # live() lo esige (DR5): una pagina non resa non è reattiva.
        self._live_enabled: bool = False
        # RX livello 0 — stato della sezione live (DR4/DR6/DR7). Privati,
        # non parte dell'API: l'unico accesso pubblico è il context
        # manager live(). Il lock serializza le sezioni (sync, re-entry).
        self._live_target: Any = None
        self._live_active: bool = False
        self._live_lock: threading.RLock = threading.RLock()
        # RX — sorgenti di risoluzione delle ``func`` dei data-element
        # (property ``data_logic``, lazy + cached). None = non ancora
        # costruita; ``_build_data_logic`` la popola al primo accesso.
        self._data_logic: list[Any] | None = None

    # ------------------------------------------------------------------
    # Lifecycle (decision 5)
    # ------------------------------------------------------------------

    def create(self) -> None:
        """Run the construction phase, then arm the reactive subscribes.

        Sequence:
            1. ``self.setup()`` populates initial data (override point;
               no-op by default). Runs first so ``main`` can read
               ``self.data`` — e.g. loop over keys to build repeated
               structure.
            2. ``self.main(self.source)`` builds the document. Subscribes
               are not active yet, so the inserts from the builder API
               do NOT dispatch to ``on_source_change``.
            3. ``self.pointer_map`` is populated lazily at read time, when
               the first render reads the pointers (not here): see
               ``_register_path``.
            4. First calculation: query the source for the data-elements to
               run at start — every ``data_setter`` (it seeds the data) plus
               any ``data_formula`` / ``data_controller`` flagged
               ``_on_start`` — and run them through :meth:`compute_logic`.
               Subscribes are not armed yet, so these writes seed the data
               without firing a reactive cascade.
            5. ``_sourceroot``/``_dataroot`` are subscribed: from here on
               every mutation flows to ``on_source_change`` /
               ``on_data_change``.
            6. ``_live_enabled`` is set: reactivity is now armed and
               ``live()`` is allowed (DR5).
        """
        self.setup()
        self.main(self.source)
        # The pointer_map is populated lazily, as runtime_values reads each
        # ^ pointer during the first render (not by an a-priori walk here).
        self.compute_logic(
            self.source.query(
                what="#n", deep=True,
                condition=lambda n: bool(
                    n._get_meta("data_element")
                    and (n.node_tag == "data_setter" or n.attr.get("_on_start"))
                ),
            )
        )
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

    @contextmanager
    def live(self, target: Any = None) -> Iterator[BuilderHandler]:
        """Open a critical section where every source/data mutation
        triggers a fresh full render (RX livello 0, DR1-DR7).

        Inside the ``with`` block, each mutation routed through
        ``_on_source_event`` / ``_on_data_event`` re-renders the whole
        document (DR3). With an explicit ``target`` the render goes there;
        without one the hooks call ``render(target=None)``, which falls
        back to the default target registered via ``set_render_target``
        (DR2). Outside the block the handler stays pull-only: no
        auto-render (DR6). The section is synchronous and serialized by an
        ``RLock`` (DR4); re-entry on the same thread is allowed and the
        parent state is restored on exit.

        Args:
            target: Optional render target. Accepts whatever
                ``RendererBase.finalize`` accepts: a filesystem path
                (str or Path), a writable file-like with ``.write()``,
                or a callable. ``None`` uses the handler's default target.

        Extension points: :meth:`on_live_enter` runs once when the section
        opens, :meth:`on_live_exit` once when it closes (also on exception,
        from the ``finally``). Subclasses override them for per-section
        setup/teardown — e.g. emitting an extra raw rendering at the end of
        a batch of mutations. Both default to no-ops.

        Raises:
            RuntimeError: reactivity not enabled — no render yet (DR5). A
            page must do its first render to finish startup before live().
        """
        if not self._live_enabled:
            raise RuntimeError(
                "live() called before the first render; render once to "
                "finish startup, then enter live()",
            )
        with self._live_lock:
            prev_active = self._live_active
            prev_target = self._live_target
            self._live_active = True
            self._live_target = target
            self.on_live_enter()
            try:
                yield self
            finally:
                self.on_live_exit()
                self._live_active = prev_active
                self._live_target = prev_target

    def on_live_enter(self) -> None:
        """Override point: runs once when a ``live()`` section opens.

        Default no-op. Subclasses use it for per-section setup. The section
        is already active (``_live_active`` is True) when this runs.
        """

    def on_live_exit(self) -> None:
        """Override point: runs once when a ``live()`` section closes.

        Default no-op. Runs from the ``finally`` of ``live()``, so it fires
        even if the body raised. The section is still active when this runs
        (the parent state is restored right after). Subclasses use it for
        per-section teardown — e.g. a final extra rendering.
        """

    def render(
        self,
        startnode: Any = None,
        mode: str | None = None,
        target: Any = None,
        **opts: Any,
    ) -> Any:
        """Render the source via the renderer bound to ``mode``.

        ``startnode`` defaults to the source wrapper node
        (``self.source.parent_node``) — the root of the user's
        document, the same node ``main()`` populates. Pass an
        explicit node to render a subtree.

        ``mode`` resolution:

        - explicit ``mode`` argument wins;
        - otherwise the handler's ``_default_render_mode`` (set via
          ``set_render_target(..., default=True)``);
        - otherwise the builder's ``_default_render_mode``.

        ``target`` semantics (decision 6 v0.4.0):

        - ``False`` → forces return-as-string, ignores any registered
          target for the chosen mode;
        - any other falsy value (``None``, ``""``, ``0``) → falls back
          to the target registered under ``mode`` (see
          ``set_render_target``);
        - truthy value → used directly as the target for this call.

        Flow: instantiate an ephemeral main renderer (R0) from the
        builder's ``renderer_<mode>`` property, seed its cache with
        itself, run the walk on ``startnode``, then finalize the
        result through R0's ``finalize``. The same ``opts`` reach both
        the walk (per-node options like ``pretty``) and ``finalize``
        (document-level options like ``doc_header``).
        """
        # The first render finishes startup: from here the pointer_map is
        # populated (read-time) and live() is allowed.
        self._live_enabled = True
        main_renderer = self._get_renderer(mode)
        effective_target = self._get_target(target, main_renderer)
        if startnode:
            # live partial render: re-render a single changed subtree
            result = main_renderer.render(startnode, **opts)
        else:
            # full render: walk the whole document from the source
            result = main_renderer.render_children(
                main_renderer.preprocess(self.source), **opts,
            )
        return main_renderer.finalize(result, effective_target, **opts)

    def _get_renderer(self, mode: str | None) -> Any:
        """Resolve the mode (explicit, else handler default, else builder
        default) and return the renderer for it, created lazily.

        The renderer instance comes from the builder's ``renderer_<mode>``
        property (looked up on the class to bypass the grammar
        ``__getattr__``) and is cached in ``self.renderers``. ``KeyError``
        if no such property exists.
        """
        mode = mode or self._default_render_mode or self.builder._default_render_mode
        renderer = self.renderers.get(mode)
        if renderer is None:
            prop = getattr(type(self.builder), f"renderer_{mode}", None)
            if prop is None:
                raise KeyError(
                    f"{type(self.builder).__name__} does not expose a "
                    f"'renderer_{mode}' property",
                )
            renderer = prop.__get__(self.builder, type(self.builder))
            renderer.handler = self
            self.renderers[mode] = renderer
        return renderer

    def _get_target(self, target: Any, renderer: Any) -> Any:
        """Resolve the render target for a render call.

        - ``False`` → return-as-value: ``None`` for a string renderer, an
          error for an object renderer (no string to return);
        - any other falsy value → the default registered for the
          renderer's mode (``None`` if none);
        - a truthy value → used as-is.
        """
        if target is False:
            if renderer.render_type != "string":
                raise TypeError(
                    f"target=False (return-as-value) is not valid for an "
                    f"object renderer ({type(renderer).__name__})",
                )
            return None
        return target or self._default_targets.get(renderer.mode)

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
        self._default_targets[mode] = target
        if default:
            self._default_render_mode = mode

    # ------------------------------------------------------------------
    # Renderer property (decision 8)
    # ------------------------------------------------------------------

    @property
    def renderer(self) -> Any:
        """Dialect renderer for the builder's default mode.

        Available for inspection (``handler.renderer._STYLE_ROOTS``,
        etc.) or for explicit calls when the shortcut
        ``handler.render(...)`` is too narrow. The instance is created
        on first access and cached in ``self.renderers``.
        """
        return self._get_renderer(None)

    def new_root(self) -> SourceBag:
        """Shortcut for ``self.builder.new_root()``.

        Returns a throw-away ``SourceBag`` driven by this handler's
        builder, with no handler attached. See ``BuilderBase.new_root``
        for the full contract.
        """
        return self.builder.new_root()

    def pyrequires(self, *mixins: type | list[type] | tuple[type, ...]) -> None:
        """Declare the component mixins this page requires.

        Enriches this handler's builder grammar with the @component
        methods carried by the given mixin classes. Call before
        ``create()`` (e.g. at the top of ``setup``/``main``).

        Polymorphic: accepts classes as varargs or a single list/tuple
        of classes (flattened one level):

            self.pyrequires(MyComponents, ExtraComp)
            self.pyrequires([MyComponents, ExtraComp])

        First member of the ``<domain>requires`` family (py / js / css /
        ...): ``pyrequires`` lives on the base because enriching the
        grammar with components is dialect-agnostic; ``jsrequires`` /
        ``cssrequires`` belong to the web layer.
        """
        flat: list[type] = []
        for item in mixins:
            if isinstance(item, (list, tuple)):
                flat.extend(item)
            else:
                flat.append(item)
        self.builder.include_components(*flat)

    # ------------------------------------------------------------------
    # Wrapper-root subscriptions (decision 11 + HWR refactor)
    # ------------------------------------------------------------------

    def _on_source_event(self, node: SourceBagNode, evt: str, **kw: Any) -> None:
        """Internal dispatcher for events on ``_sourceroot``.

        First maintains ``self.pointer_map`` coherent across the
        mutation (DAT.2), then forwards a normalized event to the user
        hook :meth:`on_source_change`. Mapkeep is structural, not
        user-facing: it MUST happen even if the user does not override
        the public hook (and overriding the hook does NOT bypass it).
        Finally, when inside a ``live(...)`` section, re-renders the
        whole document to the live target (RX livello 0, DR3).
        """
        if evt == "ins":
            self.on_source_change(node, "ins", evt_detail=None, **kw)
        elif evt == "del":
            self._unregister_pointer(node)
            self.on_source_change(node, "del", evt_detail=None, **kw)
        else:
            detail = evt[4:] if evt.startswith("upd_") else evt
            if detail in ("value", "value_attr"):
                self._on_upd_value(node, kw.get("oldvalue"))
            if detail in ("attrs", "value_attr"):
                self._on_upd_attrs(node, kw.get("attrs_diff") or {})
            self.on_source_change(node, "upd", evt_detail=detail, **kw)
        if self._live_active:
            self.render(target=self._live_target)

    def _on_data_event(self, node: SourceBagNode, evt: str, **kw: Any) -> None:
        """Internal dispatcher for events on ``_dataroot``.

        Runs :meth:`compute_logic` for the mutated path FIRST (so dependent
        data-elements are recomputed before the user hook and the live
        re-render see the new state), then forwards a normalized event to
        :meth:`on_data_change`. Finally, when inside a ``live(...)`` section,
        re-renders the whole document (RX livello 0, DR3).

        Path derivation differs by event kind (genro_bag ``pathlist``
        convention): for ``upd`` the pathlist already includes the node, so
        ``pathlist[1:]``; for ``ins`` the pathlist stops at the parent, so the
        node's own ``label`` is appended. This makes a data-element born from a
        chained formula (``base = x + y`` written for the first time) propagate
        to its dependents (``area = base * h``). ``del`` is out of scope.

        On ``ins`` the compute is skipped when ``reason == "autocreate"``: that
        marks the structural birth of an intermediate container (e.g. ``tri``
        born when ``tri.x`` is first written), which must not run dependents
        while the leaves are still absent. genro_bag tags these events
        (genro-bag #53); the leaf-datum insert carries no such reason. This
        mirrors the legacy ``gnrdomsource.js`` ``getTriggerReason`` early-out.
        """
        if evt == "ins":
            if kw.get("reason") != "autocreate":
                path = ".".join([*kw["pathlist"][1:], node.label])
                self.compute_logic(self._nodes_to_compute(path))
            self.on_data_change(node, "ins", evt_detail=None, **kw)
        elif evt == "del":
            self.on_data_change(node, "del", evt_detail=None, **kw)
        else:
            detail = evt[4:] if evt.startswith("upd_") else evt
            path = ".".join(kw["pathlist"][1:])
            self.compute_logic(self._nodes_to_compute(path))
            self.on_data_change(node, "upd", evt_detail=detail, **kw)
        if self._live_active:
            self.render(target=self._live_target)

    def node_by_id(self, node_id: str) -> SourceBagNode:
        """Return the source node carrying ``node_id``.

        Walk-based lookup over the source tree. Raises ``KeyError`` if
        no node carries the requested id.
        """
        node = self.source.get_node_by_attr("node_id", node_id)
        if node is None:
            raise KeyError(node_id)
        return node

    # ------------------------------------------------------------------
    # Reactive cascade (compute)
    # ------------------------------------------------------------------

    def _nodes_to_compute(self, path: str) -> list[SourceBagNode]:
        """Collect the data-element nodes that depend on a mutated ``path``.

        Three matches against ``pointer_map`` (whose keys are absolute data
        paths, optionally suffixed ``?attr``), comparing the path part
        ``kp = key.split("?", 1)[0]`` with the mutated ``path``:

        - node    — ``kp == path``: reads exactly the mutated datum;
        - container — ``kp.startswith(path + ".")``: reads a leaf inside the
          mutated container;
        - child   — ``path.startswith(kp + ".")``: reads a container whose
          child changed.

        Only data-element nodes are kept (``_is_data_element``): plain view
        nodes that happen to read the same path are not recomputed. Data-setters
        carry no ``^`` pointer, so they never appear in ``pointer_map`` and are
        excluded by construction. Deduped by ``id(node)`` (a node may match
        from several keys).
        """
        seen: dict[int, SourceBagNode] = {}
        for key, inner in self.pointer_map.items():
            kp = key.split("?", 1)[0]
            if kp == path or kp.startswith(path + ".") or path.startswith(kp + "."):
                for node_id, node in inner.items():
                    if node._get_meta("data_element"):
                        seen[node_id] = node
        return list(seen.values())

    def compute_logic(self, nodes: Iterable[SourceBagNode]) -> None:
        """Execute a list of data-element nodes.

        The single executor, shared by both entry points: the first
        calculation in :meth:`create` (nodes from a source query) and the
        reactive cascade (nodes from :meth:`_nodes_to_compute`). The caller
        does the collection; this only runs each node through
        :meth:`_compute_node`.

        Slice 1 — first collect only: no queue, no second wave. The writes
        performed by each :meth:`_compute_node` re-fire ``_on_data_event``
        synchronously (genro_bag is re-entrant), but the nested collect filters
        ``_is_data_element`` and, in this slice's scope (writes touch only
        rendered values, no data-element downstream), returns an empty list —
        the nested pass is inert by construction.
        """
        for node in nodes:
            self._compute_node(node)

    def _compute_node(self, node: SourceBagNode) -> None:
        """Execute a single data-element node according to its kind.

        ``kind`` is the node tag (``data_formula`` / ``data_controller``).
        Bindings are resolved ALWAYS through the node's :meth:`runtime_values`
        — the single resolution point for ``^``/``=`` pointers, ``${}``
        templates and (future) defaults that every reader uses (a div reading
        ``^.title`` no less than a formula reading ``^.base``). The resolved
        attrs are then stripped of the schema fields (``destination`` /
        ``func`` / ``value``) and the internal markers (``_...``); what remains
        are the bindings. ``func`` is a name resolved to a ``@staticmethod``
        through :meth:`_resolve_logic_func`.

        - ``data_formula`` is pure: ``func(**bindings)`` -> written at
          ``destination``;
        - ``data_controller`` has side effects: ``func(node, **bindings)``
          (``node`` explicit; the func is static, so no ``self``).
        """
        match node.node_tag:
            case "data_setter":
                # First-calculation seed: write the setter's value (held as a
                # flat attr, may be a Bag) at its destination. No func, no
                # bindings.
                node.set_relative_data(node.attr["destination"], node.attr["value"])
            case "data_formula":
                func = self._resolve_logic_func(node.attr["func"])
                node.set_relative_data(
                    node.attr["destination"], func(**self._bindings(node)),
                )
            case "data_controller":
                func = self._resolve_logic_func(node.attr["func"])
                func(node, **self._bindings(node))

    def _bindings(self, node: SourceBagNode) -> dict[str, Any]:
        """Resolve a data-element node's bindings via :meth:`runtime_values`.

        The single resolution point (``^``/``=`` pointers, ``${}`` templates,
        defaults) shared with every reader. ``runtime_values`` already drops
        the structural meta-attributes; here we strip the element's own schema
        fields — ``destination`` / ``func`` / ``value`` and the control flag
        ``_on_start``, all declared in the data-element signature — so what
        remains are the bindings passed to the func by kwarg name.
        """
        info = self.builder._get_schema_info(node.node_tag)
        fields = set(info.get("call_args_validations") or {})
        _, resolved = node.runtime_values()
        return {
            name: value
            for name, value in resolved.items()
            if name not in fields
        }

    @property
    def data_logic(self) -> list[Any]:
        """Sources searched (left-to-right) to resolve a data-element ``func``.

        Lazy + cached on ``_data_logic``. Default is ``[self]`` (the handler
        itself, zero-config). Subclasses override :meth:`_build_data_logic`
        to return a dedicated logic object or a list of them.
        """
        if self._data_logic is None:
            built = self._build_data_logic()
            self._data_logic = (
                list(built) if isinstance(built, (list, tuple)) else [built]
            )
        return self._data_logic

    def _build_data_logic(self) -> Any:
        """Override point: return the data_logic source(s). Default ``self``.

        A subclass may return a single instance or a list; both are
        normalized to a list by the :attr:`data_logic` property.
        """
        return self

    def _resolve_logic_func(self, name: str) -> Any:
        """Resolve ``name`` to a ``@staticmethod`` over ``data_logic`` sources.

        Left-to-right, first-wins. A source that does not own the name is
        skipped. A source that owns the name but NOT as a ``staticmethod``
        raises ``TypeError`` (the name is found but malformed — no silent
        fall-through). Miss on every source raises ``AttributeError``.
        ``inspect.getattr_static`` is used so the check ignores any
        ``__getattr__`` dispatch and sees the real attribute.
        """
        for source in self.data_logic:
            try:
                attr = inspect.getattr_static(source, name)
            except AttributeError:
                continue
            if not isinstance(attr, staticmethod):
                raise TypeError(
                    f"data-element func {name!r} on {type(source).__name__} "
                    "must be a @staticmethod",
                )
            return getattr(source, name)
        sources = ", ".join(type(s).__name__ for s in self.data_logic)
        raise AttributeError(
            f"data-element func {name!r} not found on any data_logic "
            f"source ({sources})",
        )

    # ------------------------------------------------------------------
    # Pointer map (DAT.2)
    # ------------------------------------------------------------------

    def _unregister_pointer(self, node: SourceBagNode) -> None:
        """Drop ``node`` (and its subtree) from ``self.pointer_map``.

        The add side is the render's job (read-time ``_register_path``);
        removal is the explicit action, because a re-render never visits
        the nodes that disappeared. Recurses into the ``SourceBag``
        subtree so a removed branch is fully purged. Silent when a path
        or node is not registered.
        """
        self._update_pointer_map(node, node.pointers())
        if isinstance(node.value, SourceBag):
            for child in node.value:
                self._unregister_pointer(child)

    def _update_pointer_map(
        self,
        node: SourceBagNode,
        pointers: list[tuple[str, str]],
    ) -> None:
        """Remove ``pointers`` of ``node`` from ``self.pointer_map``.

        Each entry is ``(attrname, pointer_str)``: ``attrname=""`` for a
        pointer on ``node.value``, otherwise the attribute name. The path
        entry is pruned when it becomes empty.
        """
        for attrname, pointer in pointers:
            path = node.abs_datapath(pointer)
            if attrname:
                path = f"{path}?{attrname}"
            inner = self.pointer_map.get(path)
            if inner is not None:
                inner.pop(id(node), None)
                if not inner:
                    del self.pointer_map[path]

    def _register_path(self, node: SourceBagNode, abs_path: str) -> None:
        """Register ``node`` as a reader of ``abs_path`` (read-time tracking)."""
        self.pointer_map.setdefault(abs_path, {})[id(node)] = node

    def _value_nature(self, v: Any) -> str:
        """Classify a value as ``"bag"``, ``"pointer"`` or ``"scalar"``.

        Used by :meth:`_on_upd_value` to dispatch over the 9-cases matrix
        of value transitions (old kind × new kind).
        """
        if isinstance(v, Bag):
            return "bag"
        if isinstance(v, str) and v.startswith("^"):
            return "pointer"
        return "scalar"

    def _on_upd_value(self, node: SourceBagNode, oldvalue: Any) -> None:
        """De-register the old value's pointers across an ``upd_value`` event.

        Dispatches over the 9 transitions of (old kind, new kind) where
        each kind is one of ``"scalar"``, ``"pointer"``, ``"bag"`` — see
        :meth:`_value_nature`. Only the OLD side acts: registration of the
        new value is the render's job (read-time ``_register_path``). The
        empty branches are kept explicit as anchor points for the future
        partial-render refactor.
        """
        new = node.value
        old_kind = self._value_nature(oldvalue)
        new_kind = self._value_nature(new)
        match (old_kind, new_kind):
            case ("scalar", "scalar"):
                pass
            case ("scalar", "pointer"):
                pass
            case ("scalar", "bag"):
                pass
            case ("pointer", "scalar"):
                self._update_pointer_map(node, [("", oldvalue)])
            case ("pointer", "pointer"):
                self._update_pointer_map(node, [("", oldvalue)])
            case ("pointer", "bag"):
                self._update_pointer_map(node, [("", oldvalue)])
            case ("bag", "scalar"):
                for old_child in oldvalue:
                    self._unregister_pointer(old_child)
            case ("bag", "pointer"):
                for old_child in oldvalue:
                    self._unregister_pointer(old_child)
            case ("bag", "bag"):
                for old_child in oldvalue:
                    self._unregister_pointer(old_child)

    def _on_upd_attrs(self, node: SourceBagNode, attrs_diff: dict) -> None:
        """De-register old attr-pointers across an ``upd_attrs`` event.

        ``attrs_diff`` is the per-attribute diff produced by ``genro_bag``:
        ``{attr_name: {"old": old_value, "new": new_value}, ...}``. Only
        the old pointer is de-registered; the new one is re-registered by
        the render that follows.
        """
        for attrname, change in attrs_diff.items():
            old_v = change.get("old")
            if isinstance(old_v, str) and old_v.startswith("^"):
                self._update_pointer_map(node, [(attrname, old_v)])

    # ------------------------------------------------------------------
    # Runtime evaluation (slice 0)
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Reactive hooks (subtask handler_wrapper_root, P2)
    # ------------------------------------------------------------------

    def on_source_change(
        self,
        node: SourceBagNode,
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
        node: SourceBagNode,
        evt: str,
        evt_detail: str | None = None,
        **kw: Any,
    ) -> None:
        """Override point. Called for every insert/update/delete on data.

        Same protocol as :meth:`on_source_change` but for the ``data``
        wrapper. Default implementation is a no-op.
        """

    # ------------------------------------------------------------------
    # User hooks
    # ------------------------------------------------------------------

    def setup(self) -> None:
        """Override point: populate initial data before ``main`` runs.

        Called first by :meth:`create`, before :meth:`main`. Default no-op.
        Use it to seed ``self.data`` so ``main`` can read it — e.g. loop
        over data keys to generate repeated structure. Keeps the data
        (setup) and the structure (main) as two clearly separate steps.
        """

    def main(self, root: SourceBag) -> None:
        """Override in subclass to populate the source bag."""
        raise NotImplementedError(
            f"{type(self).__name__}.main(root) must be implemented by the subclass",
        )
