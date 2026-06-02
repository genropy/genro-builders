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

import inspect
import threading
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from typing import Any

from genro_bag import Bag

from .builder import BagBuilderBase
from .builder_bag import BuilderBag, BuilderBagNode
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
        self._sourceroot: BuilderBag = BuilderBag(
            builder=self.builder, handler=self,
        )
        self._dataroot: BuilderBag = BuilderBag(
            builder=self.builder, handler=self,
        )
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
        # DAT.2 — mappa delle dipendenze pointer popolata da
        # ``register_pointer``. Chiave esterna = path assoluto (output di
        # ``abs_datapath``); valore = dict ``{id(node): node}`` (BuilderBagNode
        # non è hashable, indicizziamo per ``id`` per add/remove O(1)).
        self.pointer_map: dict[str, dict[int, BuilderBagNode]] = {}
        # RX livello 0 — flag di abilitazione reattività: acceso da
        # create() dopo aver armato le subscribe. live() lo esige (DR5):
        # senza, una mutazione resterebbe muta (subscribe non armate) e
        # render() su un documento non costruito darebbe stringa vuota.
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

    def _ensure_mode(self, mode: str) -> dict[str, Any]:
        """Return the ``self.renderers[mode]`` entry, creating it lazily.

        Each entry holds ``{"target": ..., "instance": RendererBase}``.
        The renderer instance is requested from the builder's
        ``renderer_<mode>`` property the first time the mode is touched
        (either by ``set_render_target`` or by ``render``). Lookup is
        on the builder *class* (not the instance) to bypass the grammar
        ``__getattr__`` that would otherwise intercept every attribute
        and produce a wrapper function. ``KeyError`` if no property
        matches the requested mode.
        """
        entry = self.renderers.get(mode)
        if entry is None:
            prop = getattr(type(self.builder), f"renderer_{mode}", None)
            if prop is None:
                raise KeyError(
                    f"{type(self.builder).__name__} does not expose a "
                    f"'renderer_{mode}' property",
                )
            renderer = prop.__get__(self.builder, type(self.builder))
            renderer.handler = self
            entry = {"target": None, "instance": renderer}
            self.renderers[mode] = entry
        return entry

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
            3. ``register_pointer`` walks the subtree rooted at the
               source wrapper node (``self.source.parent_node``) and
               populates ``self.pointer_map`` once.
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
        self.register_pointer(self.source.parent_node)
        self.compute_logic(
            self.source.query(
                what="#n", deep=True,
                condition=lambda n: bool(
                    n.attr.get("_is_data_element")
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
        self._live_enabled = True

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
            RuntimeError: reactivity not enabled — create() not run (DR5).
        """
        if not self._live_enabled:
            raise RuntimeError(
                "live() called before create(); reactivity not enabled",
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
        result through R0's ``finalize`` (which dispatches to the
        renderer's shape-specific finalize method).
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
        r0 = entry["instance"]
        r0.mode = effective_mode
        r0.add_render(self.builder, r0)
        if startnode is None:
            startnode = self.source
        result = r0.render(startnode, **opts)
        return r0.finalize(result, effective_target)

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

    def new_root(self) -> BuilderSource:
        """Shortcut for ``self.builder.new_root()``.

        Returns a throw-away ``BuilderSource`` driven by this handler's
        builder, with no handler attached. See ``BagBuilderBase.new_root``
        for the full contract.
        """
        return self.builder.new_root()

    # ------------------------------------------------------------------
    # Sub-builder access (decision 2)
    # ------------------------------------------------------------------

    def get_subbuilder(self, name: str) -> Any:
        """Return a sub-builder instance by canonical name.

        Looks up the class in the global registry via
        :meth:`BagBuilderBase.get_builder_class` and instantiates it.
        """
        return BagBuilderBase.get_builder_class(name)()

    # ------------------------------------------------------------------
    # Wrapper-root subscriptions (decision 11 + HWR refactor)
    # ------------------------------------------------------------------

    def _on_source_event(self, node: BuilderBagNode, evt: str, **kw: Any) -> None:
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
            self.register_pointer(node)
            self.on_source_change(node, "ins", evt_detail=None, **kw)
        elif evt == "del":
            self.register_pointer(node, unregister=True)
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

    def _on_data_event(self, node: BuilderBagNode, evt: str, **kw: Any) -> None:
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

    def node_by_id(self, node_id: str) -> BuilderBagNode:
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

    def _nodes_to_compute(self, path: str) -> list[BuilderBagNode]:
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
        seen: dict[int, BuilderBagNode] = {}
        for key, inner in self.pointer_map.items():
            kp = key.split("?", 1)[0]
            if kp == path or kp.startswith(path + ".") or path.startswith(kp + "."):
                for node_id, node in inner.items():
                    if node.attr.get("_is_data_element"):
                        seen[node_id] = node
        return list(seen.values())

    def compute_logic(self, nodes: Iterable[BuilderBagNode]) -> None:
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

    def _compute_node(self, node: BuilderBagNode) -> None:
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

    def _bindings(self, node: BuilderBagNode) -> dict[str, Any]:
        """Resolve a data-element node's bindings via :meth:`runtime_values`.

        The single resolution point (``^``/``=`` pointers, ``${}`` templates,
        defaults) shared with every reader. The resolved attrs are stripped of
        the schema fields (``destination`` / ``func`` / ``value``) and the
        internal markers (``_...``); what remains are the bindings passed to
        the func by kwarg name.
        """
        info = self.builder._get_schema_info(node.node_tag)
        fields = set(info.get("call_args_validations") or {})
        _, resolved = node.runtime_values()
        return {
            name: value
            for name, value in resolved.items()
            if not name.startswith("_") and name not in fields
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

    def register_pointer(self, node: BuilderBagNode, unregister: bool = False) -> None:
        """Update ``self.pointer_map`` for the subtree rooted at ``node``.

        Walks the subtree recursively. For each visited node, collects
        every pointer string it carries (a ``str`` value starting with
        ``^``, either as ``node.value`` or as any entry of ``node.attr``)
        and updates ``self.pointer_map`` accordingly.

        Map key — the granularity is **per-attribute**, so a consumer of
        the future reactive notification knows exactly which attribute
        of the node changed (and can update only that, without
        rebuilding):

            - pointer on ``node.value``    → key = ``abs_datapath(node, pointer)``
            - pointer on ``node.attr[a]``  → key = ``abs_datapath(node, pointer) + "?" + a``

        Map value: ``{id(node): node}`` (``BuilderBagNode`` is not
        hashable, so we index by ``id`` for O(1) add/remove).

        ``unregister=False`` (default) — add. ``unregister=True`` —
        remove; the path entry is pruned from ``self.pointer_map`` when
        it becomes empty. Remove is **silent** when the path or the
        node is not registered: tolerates partial-registration scenarios
        (e.g. a subtree built outside the normal flow).

        Errors from ``abs_datapath`` (``ValueError`` for unresolved
        relative paths, ``KeyError`` for unknown symbolic anchors) are
        propagated.
        """
        self._update_pointer_map(node, node.pointers(), unregister)
        # Recurse only into builder structure (BuilderBag), never into a plain
        # Bag value: that is data payload (e.g. a data_setter whose value is a
        # Bag), whose children are plain BagNodes without ``pointers()``. The
        # source tree to index is made of BuilderBag/BuilderSourceNode.
        if isinstance(node.value, BuilderBag):
            for child in node.value:
                self.register_pointer(child, unregister=unregister)

    def _update_pointer_map(
        self,
        node: BuilderBagNode,
        pointers: list[tuple[str, str]],
        unregister: bool,
    ) -> None:
        """Apply add/remove on ``self.pointer_map`` for ``pointers`` of ``node``.

        Each entry of ``pointers`` is ``(attrname, pointer_str)``:
        ``attrname=""`` for a pointer on ``node.value``, otherwise the
        attribute name. The key composition rule is documented in
        :meth:`register_pointer`.
        """
        for attrname, pointer in pointers:
            path = node.abs_datapath(pointer)
            if attrname:
                path = f"{path}?{attrname}"
            if unregister:
                inner = self.pointer_map.get(path)
                if inner is not None:
                    inner.pop(id(node), None)
                    if not inner:
                        del self.pointer_map[path]
            else:
                self.pointer_map.setdefault(path, {})[id(node)] = node

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

    def _on_upd_value(self, node: BuilderBagNode, oldvalue: Any) -> None:
        """Keep ``self.pointer_map`` coherent across an ``upd_value`` event.

        Dispatches over the 9 transitions of (old kind, new kind) where
        each kind is one of ``"scalar"``, ``"pointer"``, ``"bag"`` —
        see :meth:`_value_nature`. The actions are:

        - on ``"scalar"`` boundary: nothing to do for that side
        - on ``"pointer"`` boundary: add/remove the direct entry of ``node``
        - on ``"bag"`` boundary: walk the (old or new) subtree
        """
        new = node.value
        old_kind = self._value_nature(oldvalue)
        new_kind = self._value_nature(new)
        match (old_kind, new_kind):
            case ("scalar", "scalar"):
                pass
            case ("scalar", "pointer"):
                self._update_pointer_map(node, [("", new)], unregister=False)
            case ("scalar", "bag"):
                for child in new:
                    self.register_pointer(child)
            case ("pointer", "scalar"):
                self._update_pointer_map(node, [("", oldvalue)], unregister=True)
            case ("pointer", "pointer"):
                self._update_pointer_map(node, [("", oldvalue)], unregister=True)
                self._update_pointer_map(node, [("", new)], unregister=False)
            case ("pointer", "bag"):
                self._update_pointer_map(node, [("", oldvalue)], unregister=True)
                for child in new:
                    self.register_pointer(child)
            case ("bag", "scalar"):
                for old_child in oldvalue:
                    self.register_pointer(old_child, unregister=True)
            case ("bag", "pointer"):
                for old_child in oldvalue:
                    self.register_pointer(old_child, unregister=True)
                self._update_pointer_map(node, [("", new)], unregister=False)
            case ("bag", "bag"):
                for old_child in oldvalue:
                    self.register_pointer(old_child, unregister=True)
                for child in new:
                    self.register_pointer(child)

    def _on_upd_attrs(self, node: BuilderBagNode, attrs_diff: dict) -> None:
        """Keep ``self.pointer_map`` coherent across an ``upd_attrs`` event.

        ``attrs_diff`` is the per-attribute diff produced by ``genro_bag``:
        ``{attr_name: {"old": old_value, "new": new_value}, ...}``. Only
        changed keys appear. For each entry, deregister the old pointer
        (if the old value was a pointer) and register the new one (if
        the new value is a pointer). Non-pointer values are ignored.
        """
        for attrname, change in attrs_diff.items():
            old_v = change.get("old")
            new_v = change.get("new")
            if isinstance(old_v, str) and old_v.startswith("^"):
                self._update_pointer_map(node, [(attrname, old_v)], unregister=True)
            if isinstance(new_v, str) and new_v.startswith("^"):
                self._update_pointer_map(node, [(attrname, new_v)], unregister=False)

    # ------------------------------------------------------------------
    # Runtime evaluation (slice 0)
    # ------------------------------------------------------------------

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
    # User hooks
    # ------------------------------------------------------------------

    def setup(self) -> None:
        """Override point: populate initial data before ``main`` runs.

        Called first by :meth:`create`, before :meth:`main`. Default no-op.
        Use it to seed ``self.data`` so ``main`` can read it — e.g. loop
        over data keys to generate repeated structure. Keeps the data
        (setup) and the structure (main) as two clearly separate steps.
        """

    def main(self, root: BuilderSource) -> None:
        """Override in subclass to populate the source bag."""
        raise NotImplementedError(
            f"{type(self).__name__}.main(root) must be implemented by the subclass",
        )
