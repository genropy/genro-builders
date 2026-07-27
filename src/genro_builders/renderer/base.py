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
from pathlib import Path
from typing import Any

from genro_bag import Bag

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

    @property
    def builder(self) -> Any:
        return self._builder

    # ------------------------------------------------------------------
    # Walk + sub-renderer cache
    # ------------------------------------------------------------------

    def add_render(self, builder: Any, renderer: RendererBase) -> None:
        """Pre-seed the cache with the renderer to use for ``builder``.

        Nothing in the package calls it: the renderer registers itself for
        its own builder in ``__init__`` and ``get_render`` resolves the
        foreign ones on demand. It stays as the way a host application
        overrides that resolution for a given builder.
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
            # Transparent: they ran at create(), the render only skips them.
            return None
        if node._get_meta("component"):
            return self._render_component(node, ra, **opts)
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
        values resolved, POINTERS passed through as pointers, absolutized
        at the component node (context free) — the ADDRESS must reach the
        final node the body builds, where it resolves exactly like a
        hand-written one (and, under ``include_datapath``, emits the same
        ``data-<name>-pointer``). The walk then re-enters on the tree the
        body built, so dialect dispatch, nested components and
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
                node, body, anchor, body_kwargs, opts,
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
        return [
            self._expand_block(
                node, body, anchor, {"node_label": child.label}, opts,
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
        # itself) and compose the path the wrapper carries as datapath.
        # The resolved copies are dropped from the body's kwargs —
        # machinery words, consumed. The component node's own pointers do
        # register in the pointer_map: a re-render of the document reads
        # the new value, so the block follows the data.
        iterable = runtime_attrs.pop("iterate", None)
        runtime_attrs.pop("store", None)
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
        # nothing). An absolute path is context-free by itself: it does
        # not start with ``.``, so it survives re-entering
        # ``abs_datapath`` on a node whose ancestors carry a datapath.
        # The body builds structure with it — computing on a datum is
        # data logic, and data logic belongs to data-elements.
        for name in runtime_attrs:
            raw = node.attr.get(name)
            if node.pointer_type(raw) == "^":
                runtime_attrs[name] = f"^{node.abs_datapath(raw)}"
        return body, iterable, anchor, runtime_attrs

    def _expand_block(
        self, node: Any, body: Any, anchor: Any, body_kwargs: dict,
        opts: dict,
    ) -> Any:
        """ONE expansion: throw-away root, body call, single-tree check,
        rendered fragment.

        The expansion renders with the component node's depth as offset:
        its own root is at 0, but it is emitted where the component sits,
        so ``pretty`` must indent it as a child of that place.
        """
        root = node.builder._expansion_root(datapath=anchor)
        body(root, **body_kwargs)
        roots = list(root.nodes)
        if len(roots) != 1:
            raise ValueError(
                f"component '{node.node_tag}' must build a tree, not "
                f"a forest: {len(roots)} root nodes",
            )
        opts = {**opts, "depth_offset": self._node_depth(
            node, opts.get("depth_offset", 0),
        )}
        return self.render(roots[0], **opts)

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

    def _node_depth(self, node: Any, depth_offset: int = 0) -> int:
        """Wrapper-rooted depth of ``node`` (user top-level sits at 0).

        Read off ``node.fullpath``: the path is dot-separated from the
        backref root, e.g. ``_root_.div_0.span_0``. The structural
        wrapper segment (``SOURCE_ROOT``) always contributes the leading
        segment, so ``dots - 1`` gives the user-visible depth. Backref
        is always on, so ``fullpath`` is never ``None`` for a placed
        node. Only used for ``pretty`` indentation, so a label that
        happened to contain a dot would skew indentation by one level —
        never correctness.

        A component expansion is built in a throw-away root of its own
        (``_expansion_root``), so its nodes are rooted at 0 while they
        are emitted INSIDE the document. ``depth_offset`` carries the
        component node's own depth across that boundary, which is the
        only thing the fullpath cannot know.
        """
        return max(node.fullpath.count(".") - 1, 0) + depth_offset


