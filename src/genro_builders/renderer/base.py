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

from pathlib import Path
from typing import Any

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

        Sub-builder boundary: when the node's active builder differs from
        this renderer's, the node sits across a dialect boundary (e.g.
        ``<svg>`` inside HTML). From here down the foreign dialect governs,
        so the fragment is produced by the foreign builder's renderer
        (resolved and cached via ``get_render``). The host renderer never
        renders foreign-grammar nodes with its own rules.
        """
        item, ra = node.builder.runtime_values(node)
        if node._get_meta("data_element"):
            return None
        tag, ra = self._handle_meta(node, ra)
        ra = self.adapt_attrs(ra)
        if isinstance(node.value, SourceBag):
            item = self.render_children(node.value, **opts)
        renderer = self.get_render(node.builder)
        return renderer.rendered_item(node, item, ra, tag=tag, **opts)

    def render_children(self, nodes: Any, **opts: Any) -> list[Any]:
        """Render each node in ``nodes`` and collect the fragments.

        Transparent nodes (data-elements) render to ``None`` and are
        dropped, so the list holds only real fragments in the dialect's
        output type.
        """
        return [
            frag
            for child in nodes
            if (frag := self.render(child, **opts)) is not None
        ]

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
          ``for_each`` -> ``xsl:for-each``);
        - ``render_attributes`` (framework attrs, e.g. the foreignObject
          xmlns) merge over the node's own, framework winning on clash.

        A node with neither falls back to its ``node_tag``. A node with
        no tag at all is a contract violation, not something to paper
        over with the auto-label — raise.
        """
        render_tag, render_attributes = node._get_meta(
            "render_tag,render_attributes",
        )
        tag = render_tag or node.node_tag
        if not tag:
            raise ValueError(
                f"node {node.label!r} has no tag to render "
                "(no render_tag, no node_tag)",
            )
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
        backref root, e.g. ``main.div_0.span_0``. The ``main`` wrapper
        (``self._sourceroot["main"]``) always contributes the leading
        segment, so ``dots - 1`` gives the user-visible depth. Backref
        is always on, so ``fullpath`` is never ``None`` for a placed
        node. Only used for ``pretty`` indentation, so a label that
        happened to contain a dot would skew indentation by one level —
        never correctness.
        """
        return max(node.fullpath.count(".") - 1, 0)


