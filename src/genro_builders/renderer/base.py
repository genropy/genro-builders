# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""RendererBase — base class for builder renderers.

A renderer walks a source bag and produces a textual representation.
The walk lives on the base class as a single ``render(node, **opts)``
method that recurses through ``render_children``. Each node composes its
own fragment with the renderer of its active builder (``node.builder``,
Decision 10), cached under ``id(builder)`` on the root renderer (R0) via
``get_render`` — so a node across a dialect boundary (``<svg>`` in HTML,
``<rect>`` under it) is rendered by the foreign dialect's renderer with no
boundary branch in the walk.

The base also owns ``finalize(result, target, **opts)``: it composes the
fragment list and consumes the target (path / writable / callable / return).
Subclasses override it only for a document-level option (``XmlRenderer``
reads ``doc_header``) or an object-shaped result.

Concrete renderers (HtmlRenderer, SvgRenderer, CssRenderer, XmlRenderer)
implement ``rendered_item(node, item, runtime_attrs, **opts)`` — the
dialect-specific fragment for one node, given the already-rendered children
(``item``) and the pointer-resolved runtime attributes (``runtime_attrs``).

Dialect boundary envelope: a node whose ``_meta`` declares ``render_tag``
(e.g. ``html`` in SVG) surfaces as that tag (``<foreignObject xmlns="...">``)
carrying the node's user attributes plus the ``render_attributes`` — read in
``render`` from the node ``_meta``, no host-side wrapper method.
"""

from __future__ import annotations

import keyword
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from genro_bag import Bag

from ..builder.data_handler import LAZY_PAGE_SIZE
from ..builder.source_bag import SourceBag

_TEXT_ESCAPE = str.maketrans({"&": "&amp;", "<": "&lt;", ">": "&gt;"})
_ATTR_ESCAPE = str.maketrans(
    {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"},
)

class RendererBase:
    """Base renderer. Owns the universal walk + cache + finalize.

    Concrete dialects subclass it and add ``rendered_item``; they override
    ``finalize`` only for a document-level option or an object-shaped result.
    """

    #: Output type of this renderer: ``"string"`` for markup dialects
    #: (HTML, SVG, CSS, XML) whose fragments are serialized strings,
    #: ``"object"`` for dialects that produce live objects (widgets,
    #: flowables). Governs whether ``target=False`` (return-as-value) is
    #: allowed: meaningful for ``"string"``, an error for ``"object"``.
    render_type: str = "string"

    #: The render mode this renderer serves (``"html"``, ``"svg"``, ...).
    #: A class attribute: each ``renderer_<mode>`` property maps one mode
    #: to one renderer class, so the mode is intrinsic, not injected. The
    #: base has none; concrete dialects set it. Used to look up the mode's
    #: default target and to resolve sub-builder renderers.
    mode: str | None = None

    def __init__(self, builder: Any, handler: Any = None) -> None:
        # A renderer is always bound to a builder at birth (the
        # ``renderer_<mode>`` property passes ``builder=self``). The
        # handler is attached afterwards, when it drives a render.
        self._builder = builder
        self.handler = handler
        # Cache "renderer instance for builder X", keyed by id(builder)
        # (builders are not always hashable). The renderer registers
        # itself for its own builder, so the walk hits the cache for
        # native nodes and only resolves foreign (sub-builder) nodes.
        self.renders: dict[int, RendererBase] = {id(builder): self}
        # Nodes whose minimum child cardinality is not satisfied,
        # collected fresh during the walk (no stored state to go stale):
        # ``(fullpath, [missing tags])``. The builder raises after the
        # walk unless the render was called with ``validate=False``.
        self.incomplete: list[tuple[str, list[str]]] = []

    @property
    def builder(self) -> Any:
        return self._builder

    # ------------------------------------------------------------------
    # Walk + sub-renderer cache
    # ------------------------------------------------------------------

    def add_render(self, builder: Any, renderer: RendererBase) -> None:
        """Seed the cache with a renderer for ``builder``.

        Called by the handler on R0 right after instantiation to
        register the main builder/renderer pair: the walk then hits
        the cache for every native node and only pays a property
        lookup on foreign (sub-builder) nodes.
        """
        self.renders[id(builder)] = renderer

    def get_render(self, builder: Any) -> RendererBase:
        """Return the renderer responsible for nodes of ``builder``.

        Hit the cache for repeat lookups (the common case during the
        walk); on miss resolve the sub-builder's renderer for its own
        default mode (``builder._default_render_mode``) — the SVG
        sub-renderer is asked for SVG output even when the host is
        HTML. Inject ``self.handler`` and memoise.
        ``KeyError`` if the sub-builder does not expose a
        ``renderer_<mode>`` property for its declared default mode.
        """
        rn = self.renders.get(id(builder))
        if rn is not None:
            return rn
        sub_mode = builder._default_render_mode
        prop = getattr(type(builder), f"renderer_{sub_mode}", None)
        if prop is None:
            raise KeyError(
                f"{type(builder).__name__} does not expose a "
                f"'renderer_{sub_mode}' property",
            )
        rn = prop.__get__(builder, type(builder))
        rn.handler = self.handler
        self.renders[id(builder)] = rn
        return rn

    def render(self, node: Any, **opts: Any) -> Any:
        """Walk a node and produce its rendered fragment.

        Data-elements are transparent — they return ``None``
        (the walk never emits strings, so absence of output is ``None``,
        not ``""``). For a node whose value is a structural SourceBag the
        children are rendered recursively into a nested list (``None``
        fragments from transparent children are dropped); the dialect's
        ``rendered_item`` then composes the fragment.

        Every per-node phase (meta handling, attribute adaptation,
        emission) belongs to the renderer of the node's own dialect,
        resolved up front via ``get_render``; R0 keeps only what is
        document-wide — the walk itself, the sub-renderer cache and
        ``finalize``. So an ``<svg>`` subtree inside HTML is interpreted
        by the SVG renderer throughout, and an ``html`` subtree inside
        SVG re-enters the HTML rules: the host renderer never applies
        its own rules to foreign-grammar nodes.

        One exception: the boundary envelope itself (a node marked
        ``subbuilder``). Its attributes configure the bridge — geometry,
        namespace — and stay literal: no dialect adaptation, only the
        ``render_attributes`` merge from ``_handle_meta``. This keeps
        ``<svg width=...>`` and ``<foreignObject width=...>`` sized by
        real attributes in both crossing directions.
        """
        item, ra = node.builder.runtime_values(node)
        if node._get_meta("data_element"):
            return None
        if node._get_meta("component"):
            return self._render_component(node, ra, **opts)
        # Recompute the node's minimum-cardinality check on the fly (the
        # walk visits every node anyway, the count is cheap) instead of
        # trusting an annotation that a later child removal would have
        # left stale. Collected on R0, raised after the walk.
        missing = node.builder._validate_sub_tags(
            node, node.builder._get_schema_info(node.node_tag),
        )
        if missing:
            self.incomplete.append((node.fullpath, missing))
        renderer = self.get_render(node.builder)
        tag, ra = renderer._handle_meta(node, ra)
        if not node._get_meta("subbuilder"):
            ra = renderer.adapt_attrs(ra)
        if isinstance(node.value, SourceBag):
            item = self.render_children(node.value, **opts)
        return renderer.rendered_item(node, item, ra, tag=tag, **opts)

    def _render_component(self, node: Any, runtime_attrs: dict, **opts: Any) -> Any:
        """Expand a component node and render the expansion in its place.

        The source carries the component as a named node (the clean
        recipe); the expansion is a render-time fact and is thrown away.
        The body — kept callable on the builder class by ``@component`` —
        receives a fresh throw-away root and builds the real structure
        into it: exactly ONE tree (one root element), a forest raises.
        The call's attributes saturate the body's signature: plain
        values resolved, REACTIVE POINTERS passed through as pointers,
        absolutized at the component node (``^volume:rest``, context
        free) — the ADDRESS must reach the final node the body builds,
        where it resolves exactly like a hand-written one and emits the
        write-back hook (CMP.4). The walk then re-enters on the tree
        the body built, so dialect dispatch, nested components and
        sub-builders apply as usual.
        """
        body, iterable, anchor, body_kwargs = self._expansion_inputs(
            node, runtime_attrs,
        )
        # The mode is declared by the AUTHOR (the attribute's presence),
        # never decided by the data: with ``iterate`` an empty collection
        # means zero blocks — the data-driven termination that lets a
        # self-recursive component (a tree) stop at the leaves.
        if "iterate" not in node.attr:
            return self._expand_block(
                node, body, anchor, body_kwargs, (), opts,
            )
        if iterable is None:
            return []

        # iterate: one expansion per child of the collection, each round
        # gets ONLY the child's label (the body anchors its root with
        # ``datapath='.' + node_label``, relative to the wrapper anchor).
        if not isinstance(iterable, Bag):
            raise TypeError(
                f"component '{node.node_tag}': iterate must resolve to a "
                f"Bag, got {type(iterable).__name__}",
            )
        if (
            node.attr.get("lazy")
            and opts.get("include_datapath")
            and node.builder.handler is not None
        ):
            # Lazy is a REACTIVE-render concern, like derived identity:
            # a static render has no client to scroll, so the full
            # document is its only meaningful output.
            return self._render_lazy_component(
                node, body, anchor, iterable, opts,
            )
        return [
            self._expand_block(
                node, body, anchor, {"node_label": child.label},
                (child.label,), opts,
            )
            for child in iterable.nodes
        ]

    def _expansion_inputs(
        self, node: Any, runtime_attrs: dict,
    ) -> tuple[Any, Any, Any, dict]:
        """The expansion prep shared by the walk and the per-row render:
        ``(body, iterable, anchor, body_kwargs)``."""
        builder = node.builder
        body = getattr(type(builder), node.node_tag).__get__(builder, type(builder))
        # ``store``/``iterate`` are data anchors, not values: read RAW
        # from the node (runtime_values would resolve them to the data
        # itself) and compose the segmentless path the wrapper carries as
        # datapath. The resolved copies are dropped from the body's
        # kwargs — machinery words, consumed. The component node's own
        # pointers DID register in the pointer_map (CMP.7): when the
        # record (or the collection) changes, the block re-renders.
        iterable = runtime_attrs.pop("iterate", None)
        runtime_attrs.pop("store", None)
        # ``id`` is chain machinery (the writeback identity uses it as
        # the expansion's prefix base), never a body kwarg.
        runtime_attrs.pop("id", None)
        # ``lazy`` is machinery too: the laziness opt-in of the iterate
        # (lazy-iterate contract), consumed by the walk, never a body
        # kwarg.
        runtime_attrs.pop("lazy", None)
        raw_anchor = node.attr.get("iterate") or node.attr.get("store")
        anchor = None
        if raw_anchor is not None:
            anchor = raw_anchor
            if node.pointer_type(anchor):
                anchor = anchor[1:]
            if anchor.startswith("."):
                anchor = node._compose_relative_datapath(anchor, anchor)
        # Pointer pass-through (CMP.4): a kwarg whose RAW value is a
        # reactive pointer reaches the body as a pointer, not as the
        # resolved value — resolving here would kill the address (the
        # expansion's input would carry a literal: mute to write-back).
        # Absolutized in the component node's context (the expansion
        # tree is detached, a relative form would resolve against
        # nothing); the volume syntax keeps it context-free. The body
        # builds structure with it — computing on a datum is data
        # logic, and data logic belongs to data-elements.
        for name in runtime_attrs:
            raw = node.attr.get(name)
            if node.pointer_type(raw) == "^":
                volume, _, rest = node.abs_datapath(raw).partition(".")
                runtime_attrs[name] = f"^{volume}:{rest}"
        return body, iterable, anchor, runtime_attrs

    def _expand_block(
        self, node: Any, body: Any, anchor: Any, body_kwargs: dict,
        wb_labels: tuple, opts: dict,
    ) -> Any:
        """ONE expansion: throw-away root, body call, single-tree check,
        derived identity (reactive render only), rendered fragment."""
        root = node.builder._expansion_root(datapath=anchor)
        body(root, **body_kwargs)
        roots = list(root.nodes)
        if len(roots) != 1:
            raise ValueError(
                f"component '{node.node_tag}' must build a tree, not "
                f"a forest: {len(roots)} root nodes",
            )
        if opts.get("include_datapath"):
            # Derived identity is a REACTIVE-render concern, like
            # the auto-id: the static render stays untouched.
            self._register_expansion_writeback(node, roots[0], wb_labels)
        return self.render(roots[0], **opts)

    def render_expansion_block(
        self, node: Any, label: str | None = None, **opts: Any,
    ) -> Any:
        """Render ONE expansion block of a component node — the per-row
        patch unit (CMP.7). ``label`` addresses the row of an iterate
        component (``None`` = the single store-anchored block). Same
        prep, same body, same registration as the walk: the fragment
        cannot diverge from a full render.
        """
        _item, runtime_attrs = node.builder.runtime_values(node)
        body, _iterable, anchor, body_kwargs = self._expansion_inputs(
            node, runtime_attrs,
        )
        if label is not None:
            body_kwargs = {"node_label": label}
            wb_labels: tuple = (label,)
        else:
            wb_labels = ()
        return self._expand_block(
            node, body, anchor, body_kwargs, wb_labels, opts,
        )

    def _render_lazy_component(
        self, node: Any, body: Any, anchor: Any, iterable: Any, opts: dict,
    ) -> list:
        """First paint of a lazy iterate: page 0 inline plus the marker.

        Two natures, one shape (lazy-iterate contract). An anchor with
        a ``read_only`` RESOLVER (immutable data): the query ran ONCE
        in ``runtime_values``, the snapshot parks on the handler (the
        freezed selection) and page 0 renders through the silent
        transit. A STORE-BACKED anchor (mutable data): no parking, no
        transit — the collection lives in the store, block pointers
        resolve naturally, pages slice it LIVE. Either way the MARKER
        closes the run with the FIRE lane and the baked counts; the
        client fabricates placeholders for the rest and asks pages as
        the scroll demands.
        """
        builder = node.builder
        handler = builder.handler
        base = str(node.attr.get("id") or builder.target_id(node))
        # Re-expansion starts clean: every entry under the base —
        # painted rows of ANY page, the marker — belongs to the DOM
        # this render replaces.
        builder._purge_writeback_prefix(base)
        anchor_node = handler.data.get_node(
            node.abs_datapath(node.attr["iterate"]),
        )
        lazy_resolver = (
            anchor_node.resolver if anchor_node is not None else None
        )
        fragments = []
        labels: list[str] = []
        if lazy_resolver is not None:
            total, page_size = handler.lazy_park(base, iterable)
            if total:
                snapshot, labels = handler.lazy_page(base, 0)
                with self._lazy_transit(node, snapshot):
                    for label in labels:
                        fragments.append(self._expand_block(
                            node, body, anchor, {"node_label": label},
                            (label,), opts,
                        ))
        else:
            total, page_size = len(iterable), LAZY_PAGE_SIZE
            if total:
                labels = handler.lazy_page_of(iterable, 0)
                for label in labels:
                    fragments.append(self._expand_block(
                        node, body, anchor, {"node_label": label},
                        (label,), opts,
                    ))
        # The marker wears the SAME tag as the row blocks (a tr among
        # the trs, a li among the lis: DOM validity, no per-dialect
        # marker). A build-only probe of the body reveals it: building
        # is structure, no pointer resolves, nothing renders.
        probe = builder._expansion_root(datapath=anchor)
        body(probe, node_label=labels[0] if labels else "probe")
        row_tag = list(probe.nodes)[0].node_tag
        fragments.append(self._render_lazy_marker(
            node, base, row_tag, total, page_size, opts,
        ))
        handler.lazy_subscribe(base, node)
        # A (re)render restarts the delivered set: whatever pages the
        # client had died with the DOM this run replaces.
        handler.lazy_track(base, labels, fresh=True)
        return fragments

    def render_lazy_page(self, node: Any, page: int, **opts: Any) -> str:
        """Render ONE page of a lazy iterate — the ``page`` op payload.

        Same prep, same body, same registration as any block render
        (the oracle holds). A resolver anchor serves from the parking
        through the silent transit; a store-backed anchor slices the
        LIVE collection — always current, nothing to restore.
        """
        handler = node.builder.handler
        base = str(node.attr.get("id") or node.builder.target_id(node))
        anchor_abs = node.abs_datapath(node.attr["iterate"])
        anchor_node = handler.data.get_node(anchor_abs)
        fragments = []
        if anchor_node is not None and anchor_node.resolver is not None:
            snapshot, labels = handler.lazy_page(base, page)
            with self._lazy_transit(node, snapshot):
                for label in labels:
                    block = self.render_expansion_block(node, label, **opts)
                    fragments.append(
                        "".join(block) if isinstance(block, list) else block,
                    )
        else:
            labels = handler.lazy_page_of(
                handler.data.get_item(anchor_abs), page,
            )
            for label in labels:
                block = self.render_expansion_block(node, label, **opts)
                fragments.append(
                    "".join(block) if isinstance(block, list) else block,
                )
        handler.lazy_track(base, labels)
        return "".join(fragments)

    @contextmanager
    def _lazy_transit(self, node: Any, snapshot: Any) -> Any:
        """The silent transit: the snapshot becomes the anchor's value
        for the duration of a block render — canonical API, no events,
        resolver detached — and the store comes out exactly as it went
        in: the resolver back in place, nothing deposited, no spurious
        row events.
        """
        handler = node.builder.handler
        anchor_abs = node.abs_datapath(node.attr["iterate"])
        saved = handler.data.get_node(anchor_abs).resolver
        handler.data.set_item(
            anchor_abs, snapshot, resolver=False, do_trigger=False,
        )
        try:
            yield
        finally:
            handler.data.set_item(
                anchor_abs, None, resolver=saved, do_trigger=False,
            )

    def _render_lazy_marker(
        self, node: Any, base: str, tag: str, total: int, page_size: int,
        opts: dict,
    ) -> Any:
        """The lazy marker: an empty element closing the page-0 run.

        Wears ``tag`` — the row blocks' own root tag — and carries the
        reserved FIRE lane plus the baked counts the client needs
        (total rows, page size); registered in the writeback map under
        the component's prefix — a fire target like any click target,
        with a MACHINERY id (``<base>.lazy``).
        """
        builder = node.builder
        root = builder._expansion_root()
        getattr(root, tag)(
            id=f"{base}.lazy",
            **{
                "data-fire-pointer": f"_lazy.{base}",
                "data-lazy-total": str(total),
                "data-lazy-page": str(page_size),
            },
        )
        marker = list(root.nodes)[0]
        builder._writeback_add(base, f"{base}.lazy", marker)
        return self.render(marker, **opts)

    def _register_expansion_writeback(
        self, comp_node: Any, tree_root: Any, labels: tuple,
    ) -> None:
        """Derived identity for expansion nodes — the virtual-children
        map, write-back side (CMP.7).

        Expansion nodes never get a serial of their own (they
        reincarnate); their identity is DERIVED and deterministic:
        ``<base>[.<iteration label>...].<ordinal>`` — base is the
        component node's id (serial or author's), labels are the row
        identities of the stores crossed, the ordinal follows the
        body's build order (the body is code, the rebuild is
        identical). The composite id is stamped as the author-id (the
        renderer emits it, the auto-id skips), and the WRITABLE nodes
        land in ``builder._writeback_map``: composite id -> expansion
        node — the node a mutate resolves to read dtype, validate_*,
        envelope and the write-back address. Re-expansion purges its
        own prefix first, so the map never holds stale rows.
        """
        builder = comp_node.builder
        base = comp_node.attr.get("id") or builder.target_id(comp_node)
        if base is None:
            return
        prefix = ".".join((str(base), *labels))
        builder._purge_writeback_prefix(prefix)
        handler = builder.handler
        # The cell catalog rebuilds per expansion and is identical for
        # every row (the body is code): reset, the last row wins.
        if len(labels) == 1:
            cmap = getattr(builder, "_cell_map", None)
            if cmap is None:
                cmap = builder._cell_map = {}
            cmap[base] = {}
        rule_nodes: list[Any] = []
        counter = 0
        queue = [tree_root]
        while queue:
            current = queue.pop(0)
            if current._get_meta("data_element"):
                # Row logic: cataloged, never rendered (no ordinal, no
                # id). The rule is a rule of MUTATION — loaded data is
                # trusted as-is, so a "start" has no meaning here and a
                # seeding element would be a render-time write.
                if current.node_tag == "dataSetter":
                    raise ValueError(
                        "dataSetter inside an expansion body: seeding "
                        "is a render-time write, expansions are pure "
                        "projections",
                    )
                if current.attr.get("_on_start"):
                    raise ValueError(
                        "_on_start inside an expansion body: row logic "
                        "is mutation-only (loaded data is trusted)",
                    )
                if handler is not None:
                    rule_nodes.append(current)
                continue
            counter += 1
            composite = f"{prefix}.{counter}"
            current.attr["id"] = composite
            # Only WRITE-BACK nodes enter the map: a pointer on a
            # writable attribute (value/checked), or a click target
            # (set-pointer writes a declared value, fire-pointer sends
            # an event message). A pure reader (a td showing ^.name)
            # re-renders via pointer_map, it is not a mutation target.
            writable = any(
                name in ("value", "checked")
                for name, _pointer in current.pointers()
            ) or current.attr.get("data-set-pointer") is not None \
              or current.attr.get("data-fire-pointer") is not None
            if writable:
                builder._writeback_add(prefix, composite, current)
            self._register_cell(comp_node, current, labels, counter)
            if isinstance(current.value, SourceBag):
                queue.extend(current.value.nodes)
        if handler is not None:
            raw_anchor = (
                comp_node.attr.get("iterate") or comp_node.attr.get("store")
            )
            anchor_abs = (
                comp_node.abs_datapath(raw_anchor) if raw_anchor else None
            )
            if labels:
                row_prefix = f"{anchor_abs}.{labels[-1]}"
            else:
                row_prefix = anchor_abs
            handler.set_component_rules(
                owner=str(base), anchor=anchor_abs,
                store_mode=bool(raw_anchor) and not labels,
                rule_nodes=rule_nodes, row_prefix=row_prefix,
            )

    def _register_cell(
        self, comp_node: Any, current: Any, labels: tuple, ordinal: int,
    ) -> None:
        """Catalog a patchable CELL: in-row field -> (ordinal, op).

        The body is code, so the ordinal of "who shows ``.field``" is
        the SAME for every row: the catalog is per COMPONENT, built
        once per registration. Two shapes qualify — a node whose VALUE
        is exactly one reactive pointer (a text cell) and a reactive
        ``value`` attribute (an input). The field key is the pointer's
        residual against the ROW path: a pointer landing outside the
        row (a shared header datum) is not a cell. Everything richer
        (templates, checked, nested labels) stays out: those rows fall
        back to the row replace.
        """
        if len(labels) != 1:
            return
        builder = comp_node.builder
        base = comp_node.attr.get("id") or builder.target_id(comp_node)
        cmap = getattr(builder, "_cell_map", None)
        if cmap is None:
            cmap = builder._cell_map = {}
        specs = cmap.setdefault(base, {})

        def in_row_field(pointer: str) -> str | None:
            anchor = comp_node.abs_datapath(comp_node.attr["iterate"])
            row_prefix = f"{anchor}.{labels[0]}."
            abs_path = current.abs_datapath(pointer)
            if not abs_path.startswith(row_prefix):
                return None
            return abs_path[len(row_prefix):]

        if (
            isinstance(current.value, str)
            and current.pointer_type(current.value) == "^"
        ):
            field = in_row_field(current.value)
            if field is not None:
                specs.setdefault(field, []).append((ordinal, "text", None))
        raw_value = current.attr.get("value")
        if (
            isinstance(raw_value, str)
            and current.pointer_type(raw_value) == "^"
        ):
            field = in_row_field(raw_value)
            if field is not None:
                specs.setdefault(field, []).append((ordinal, "attr", "value"))

    def render_children(self, nodes: Any, **opts: Any) -> list[Any]:
        """Render each node in ``nodes`` and collect the fragments.

        Transparent nodes (data-elements) render to ``None`` and are
        dropped, so the list holds only real fragments in the dialect's
        output type. A node whose render returns a LIST (an iterate
        component: N expansions for one source node) is flattened in
        place — the N blocks compose exactly as N siblings would.
        """
        fragments: list[Any] = []
        for child in nodes:
            frag = self.render(child, **opts)
            if frag is None:
                continue
            if isinstance(frag, list):
                fragments.extend(frag)
            else:
                fragments.append(frag)
        return fragments

    def preprocess(self, source: Any) -> Any:
        """Normalize the source bag before the top-level walk.

        Identity by default: the walk renders the source as authored.
        Dialects whose output is not a 1:1, order-preserving mapping of
        the source nodes (e.g. CSS grouping cssvars into ``:root`` and
        hoisting imports) override this to return a normalized copy —
        never mutating the user's source.
        """
        return source

    def rendered_item(
        self,
        node: Any,
        item: Any,
        runtime_attrs: dict[str, Any],
        *,
        tag: str,
        **opts: Any,
    ) -> Any:
        """Produce the dialect-specific fragment for ``node``.

        Concrete renderers override this. ``tag`` and ``runtime_attrs``
        are already resolved by the walk (``_handle_meta`` + ``adapt_attrs``),
        so the renderer only formats and emits. ``item`` is the children's
        rendered fragments (list) when the node's value is a Bag,
        otherwise the node's raw value.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not implement rendered_item",
        )

    def _handle_meta(
        self, node: Any, runtime_attrs: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        """Resolve the ``_meta`` that affects emission, once for every
        dialect, so ``rendered_item`` receives a ready tag and attrs.

        - ``render_tag`` replaces the node's tag (a sub-builder boundary:
          ``html`` -> ``foreignObject``; an XSLT instruction:
          ``for_each`` -> ``xsl:for-each``). It is for tags a method name
          cannot spell (a hyphen, a colon) — NOT for a Python-keyword
          clash, which the trailing-underscore convention resolves on its
          own (``del_`` -> ``del``, see below).
        - ``render_attributes`` (framework attrs, e.g. the foreignObject
          xmlns) merge over the node's own, framework winning on clash.
        - ``ns`` (a schema attribute, not ``_meta``) prefixes the tag:
          ``ns='xs'`` on element ``sequence`` emits ``xs:sequence``. It
          composes ``<ns>:<tag>`` from the method name AFTER the keyword
          strip (so ``import_`` -> ``import`` -> ``xs:import``), and only
          when there is no explicit ``render_tag`` (which wins, being the
          exact literal tag). A leading ``<dialect>_`` prefix on the tag
          is dropped first (``xsd_element`` -> ``xs:element``), the escape
          for a method whose bare name would shadow a decorator/API name.

        A node with neither falls back to its ``node_tag``, stripping a
        trailing ``_`` when the bare name is a Python keyword: the schema
        keeps a valid identifier (``del_``) while the markup emits the
        real tag (``del``). A node with no tag at all is a contract
        violation, not something to paper over with the auto-label — raise.
        """
        render_tag, render_attributes = node._get_meta(
            "render_tag,render_attributes",
        )
        tag = render_tag or node.node_tag
        if tag and tag.endswith("_") and keyword.iskeyword(tag[:-1]):
            tag = tag[:-1]
        if not tag:
            raise ValueError(
                f"node {node.label!r} has no tag to render "
                "(no render_tag, no node_tag)",
            )
        ns = node.get_attr("ns")
        if ns and not render_tag:
            # A method named for the dialect prefix (``xsd_element``, to
            # avoid shadowing the ``element`` decorator) drops that prefix
            # before composing the local name: ``ns='xs'`` + method
            # ``xsd_element`` -> ``xs:element``. Same escape ``_schema_tag``
            # uses for dispatch, here on the emitted local name.
            dialect_prefix = f"{node.builder._name}_"
            if tag.startswith(dialect_prefix):
                tag = tag[len(dialect_prefix):]
            tag = f"{ns}:{tag}"
        if render_attributes:
            runtime_attrs = {**runtime_attrs, **render_attributes}
        return tag, runtime_attrs

    def adapt_attrs(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Dialect-specific adaptation of the attribute dict before
        serialization. Identity by default; the extension point for any
        rewrite that produces a different *dict* (not its serialization).

        Today only ``HtmlRenderer`` overrides it, to collapse CSS roots
        and Genro macros into a single ``style`` entry. Serialization
        (``_format_attrs``) then treats the result as ordinary attrs.
        """
        return attrs

    def _format_attrs(self, attrs: dict[str, Any]) -> str:
        """Serialize an attribute dict to a markup string.

        Abstract on the base: each concrete renderer implements its own
        dialect formatting (``XmlRenderer`` here, ``HtmlRenderer`` /
        ``SvgRenderer`` in contrib). Used both when emitting a node and
        when wrapping a sub-builder fragment (``wrap_tag``).
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not implement _format_attrs",
        )

    def adapt(self, what: str) -> str:
        """Strip this dialect's own ``<name>_`` prefix from ``what``.

        ``what`` unchanged unless it starts with ``f"{builder._name}_"``,
        in which case the prefix is removed. This is the explicit escape a
        dialect offers for attribute names that would otherwise be
        intercepted (CSS roots, macros) or shadow a Python builtin:
        ``html_type`` -> ``type``, ``html_width`` -> ``width``.
        """
        prefix = f"{self.builder._name}_"
        return what[len(prefix):] if what.startswith(prefix) else what

    # ------------------------------------------------------------------
    # Finalize (target side)
    # ------------------------------------------------------------------

    def finalize(self, result: Any, target: Any, **_opts: Any) -> Any:
        """Turn the render result into the user-visible output.

        ``_opts`` mirrors the walk options the handler forwards (e.g.
        ``pretty``, ``include_datapath``); they are per-node concerns
        already consumed during the walk, so the base finalize ignores
        them. Subclasses that need a document-level option (``XmlRenderer``
        reads ``doc_header``) declare it explicitly in their override.

        The default (string dialects) joins the fragments — ``result`` is
        a list of child fragments from the top-level walk, or a single
        fragment for a subtree render — and consumes ``target``:

        - ``None`` → return the text;
        - ``str`` or ``pathlib.Path`` → treat as filesystem path,
          create parent directories if missing, write text with UTF-8
          encoding, return ``None``;
        - object with ``.write`` callable → write to file-like,
          return ``None``;
        - plain callable → invoke with the text, return ``None``.

        Object dialects (widgets, flowables) override this with their own
        composition and target handling.
        """
        if isinstance(result, list):
            result = "".join(result)
        if target is None:
            return result
        full = getattr(target, "full", None)
        if callable(full) and not callable(getattr(target, "write", None)):
            # A TargetWrapper destination: deliver the total render.
            full(result)
            return None
        if isinstance(target, (str, Path)):
            path = Path(target)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(result, encoding="utf-8")
            return None
        write = getattr(target, "write", None)
        if callable(write):
            write(result)
            return None
        if callable(target):
            target(result)
            return None
        raise TypeError(
            f"render target {target!r} is neither a path "
            "(str/Path), writable (.write), nor callable",
        )

    # ------------------------------------------------------------------
    # Shared escape helpers (used by concrete dialects)
    # ------------------------------------------------------------------

    def _escape_text(self, value: Any) -> str:
        """Escape a text value for safe inclusion in XML/HTML body."""
        return str(value).translate(_TEXT_ESCAPE)

    def _escape_attr(self, value: Any) -> str:
        """Escape an attribute value (also escapes double quotes)."""
        return str(value).translate(_ATTR_ESCAPE)

    def _node_depth(self, node: Any) -> int:
        """Wrapper-rooted depth of ``node`` (user top-level sits at 0).

        Read off ``node.fullpath``: the path is dot-separated from the
        backref root, e.g. ``_root_.div_0.span_0``. The structural
        wrapper segment (``SOURCE_ROOT``) always contributes the leading
        segment, so ``dots - 1`` gives the user-visible depth. Backref
        is always on, so ``fullpath`` is never ``None`` for a placed
        node. Only used for ``pretty`` indentation, so a label that
        happened to contain a dot would skew indentation by one level —
        never correctness.
        """
        return max(node.fullpath.count(".") - 1, 0)


