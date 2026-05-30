# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""RendererBase — base class for builder renderers.

A renderer walks a source bag and produces a textual representation.
The walk lives on the base class as a single ``render(node, **opts)``
method that recurses on itself. For each node visited the base
resolves the renderer responsible for the node (its own builder),
caches it under ``id(builder)`` on the root renderer (R0), and asks
that renderer for the local fragment via ``rendered_item``.

The base also owns ``finalize(result, target)``: a dispatcher that
looks up ``finalize_<self.finalize_method>`` on the renderer and
calls it. Concrete renderers declare ``finalize_method`` as a class
attribute; if their shape is "raw" (a ready-to-write string) they
inherit ``finalize_raw`` here and need to do nothing else.

Concrete renderers (HtmlRenderer, SvgRenderer, CssRenderer,
XmlRenderer) implement ``rendered_item(node, item, runtime_attrs,
**opts)`` — the dialect-specific fragment for one node, given the
already-rendered children (``item``) and the runtime attributes
already resolved from pointers (``runtime_attrs``).

Sub-builder polymorphism: when R0 sees a node whose builder differs
from its own, the local fragment is produced by the foreign
renderer's ``rendered_item`` (cached). If the host builder declares
a ``wrapper_<sub_name>`` method, R0 wraps the foreign fragment in
the dialect-specific envelope (e.g. SVG hosting HTML in
``<foreignObject xmlns="...">``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from genro_bag import Bag

_TEXT_ESCAPE = str.maketrans({"&": "&amp;", "<": "&lt;", ">": "&gt;"})
_ATTR_ESCAPE = str.maketrans(
    {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"},
)


class RendererBase:
    """Base renderer. Owns the universal walk + cache + finalize.

    Concrete dialects subclass it and add ``rendered_item`` plus,
    optionally, a non-``raw`` ``finalize_method`` with the matching
    ``finalize_<shape>`` method.
    """

    #: Default finalize shape: ``finalize_raw`` writes a string to the
    #: target. Concrete renderers override only if their result is not
    #: already a serialized string.
    finalize_method: str = "raw"

    def __init__(self, handler: Any = None, builder: Any = None) -> None:
        self.handler = handler
        # When ``builder`` is None the renderer falls back to
        # ``self.handler.builder``. When the builder property
        # ``renderer_<mode>`` instantiates this class it passes
        # ``builder=self`` directly so the renderer is locked to that
        # dialect even before a handler is attached.
        self._builder = builder
        # Cache of "renderer instance for builder X". Populated by R0
        # (the main renderer of a render() call) on first visit of a
        # node owned by a foreign builder. Keyed by id(builder) because
        # builders are not always hashable. Each sub-renderer is also
        # an instance of RendererBase but its own ``renders`` dict
        # stays empty: only R0 drives the walk.
        self.renders: dict[int, RendererBase] = {}
        # The render mode of the active call. Set by the handler on
        # R0 right after instantiation; ``get_render`` uses it to
        # resolve sub-builder ``renderer_<mode>`` properties.
        self.mode: str | None = None

    @property
    def builder(self) -> Any:
        return self._builder if self._builder is not None else self.handler.builder

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

    def render(self, source: Any, **opts: Any) -> Any:
        """Walk ``source`` and produce its rendered fragment.

        ``source`` may be a Bag or a BagNode. For a Bag the renderer
        emits the concatenation of each top-level child's fragment.
        For a node: ``runtime_values`` resolves pointers, children are
        rendered recursively, and the dialect's ``rendered_item``
        composes the final fragment. When the node's builder differs
        from R0's a foreign renderer is fetched via ``get_render``;
        if the host declares a ``wrapper_<sub_name>`` envelope the
        sub-builder node itself is replaced by the wrap tag and only
        its children are emitted by the sub-renderer.
        """
        if isinstance(source, Bag):
            return "".join(self.render(child, **opts) for child in source)
        node = source
        node_builder = node.builder
        if node_builder is None or node_builder is self.builder:
            item, ra = node.runtime_values()
            if isinstance(node.value, Bag):
                item = [self.render(child, **opts) for child in node.value]
            return self.rendered_item(node, item, ra, **opts)
        # Foreign builder: hand off to its renderer.
        rn = self.get_render(node_builder)
        wrapper_spec = self._wrapper_spec_for(node_builder)
        if wrapper_spec is None:
            # No envelope: the sub-builder node renders verbatim.
            return rn.render(node, **opts)
        # Envelope: the wrap tag replaces the sub-builder node, the
        # sub-renderer emits only the children.
        value = node.value
        if isinstance(value, Bag):
            children_fragment = "".join(rn.render(child, **opts) for child in value)
        elif value is None:
            children_fragment = ""
        else:
            children_fragment = rn._escape_text(value)
        return self._wrap_fragment(node, children_fragment, wrapper_spec)

    def rendered_item(
        self,
        node: Any,
        item: Any,
        runtime_attrs: dict[str, Any],
        **opts: Any,
    ) -> Any:
        """Produce the dialect-specific fragment for ``node``.

        Concrete renderers override this. ``item`` is the children's
        rendered fragments (list) when the node's value is a Bag,
        otherwise the node's raw value. ``runtime_attrs`` is the
        attribute dict already resolved through pointer expansion.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not implement rendered_item",
        )

    # ------------------------------------------------------------------
    # Sub-builder wrapper (host-dialect envelope)
    # ------------------------------------------------------------------

    def _wrapper_spec_for(self, node_builder: Any) -> dict[str, Any] | None:
        """Look up the host builder's ``wrapper_<sub_name>`` method.

        Returns the dict ``{"tag": ..., "attrs": ...}`` if declared,
        ``None`` if the host does not wrap this sub-dialect. Walks
        the MRO via ``__dict__`` to bypass the builder's ``__getattr__``
        (which dispatches grammar tags).
        """
        sub_name = getattr(node_builder, "_name", None)
        if not sub_name:
            return None
        host = self.builder
        attr_name = f"wrapper_{sub_name}"
        for klass in type(host).__mro__:
            if attr_name in klass.__dict__:
                wrapper: dict[str, Any] | None = klass.__dict__[attr_name](host)
                return wrapper
        return None

    def _wrap_fragment(
        self,
        node: Any,
        fragment: Any,
        wrapper_spec: dict[str, Any],
    ) -> str:
        """Wrap a sub-renderer fragment in the host envelope.

        Default ``raw`` implementation: the fragment is treated as a
        string, the user attributes of the wrapper node are formatted
        with the host renderer and concatenated with the framework
        attributes (e.g. ``xmlns``) declared by the wrapper spec.
        """
        wrap_tag = wrapper_spec["tag"]
        wrap_attrs = wrapper_spec.get("attrs") or {}
        user_attrs = self._format_attrs(node.attr)
        framework_attrs = self._format_attrs(wrap_attrs)
        return f"<{wrap_tag}{framework_attrs}{user_attrs}>{fragment}</{wrap_tag}>"

    def _format_attrs(self, attrs: dict[str, Any]) -> str:
        """Hook used by ``_wrap_fragment``. Override in dialects that
        host sub-builders with wrap_tag (e.g. ``HtmlRenderer`` ospitando
        SVG, ``SvgRenderer`` ospitando HTML)."""
        raise NotImplementedError(
            f"{type(self).__name__} does not implement _format_attrs",
        )

    # ------------------------------------------------------------------
    # Finalize (target side)
    # ------------------------------------------------------------------

    def finalize(self, result: Any, target: Any) -> Any:
        """Dispatch the finalization to ``finalize_<finalize_method>``.

        The finalize method is the bridge between the renderer result
        and the user-visible side: it interprets ``target`` (None →
        return the value, path/file-like/callable → consume the
        value). ``finalize_method`` is a class attribute on the
        concrete renderer; ``finalize_raw`` is the default shape
        (string-to-target) defined on this base class.
        """
        method = getattr(self, f"finalize_{self.finalize_method}")
        return method(result, target)

    def finalize_raw(self, result: Any, target: Any) -> Any:
        """Default finalize: ``result`` is a ready-to-write string.

        Accepted ``target`` shapes:

        - ``None`` → return the text;
        - ``str`` or ``pathlib.Path`` → treat as filesystem path,
          create parent directories if missing, write text with UTF-8
          encoding, return ``None``;
        - object with ``.write`` callable → write to file-like,
          return ``None``;
        - plain callable → invoke with the text, return ``None``.
        """
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

    # Backwards-compat shim: ``CssRenderer`` (kept on the legacy walk
    # for now) still uses this name internally. Aliased to
    # ``finalize_raw`` so the contract is identical.
    def _write_or_return(self, text: str, render_target: Any) -> Any:
        return self.finalize_raw(text, render_target)


class XmlRenderer(RendererBase):
    """Renderer of the shared ``xml`` mode.

    Exposed by ``BagBuilderBase.renderer_xml`` so every dialect can
    serve ``xml`` without declaring its own renderer. Concrete dialects
    that want a custom XML walk override ``renderer_xml`` on their
    builder to return a different renderer class.

    XML serialization is delegated to ``Bag.to_xml`` because pretty
    indentation and ``doc_header`` already live there. ``render`` is
    overridden to call ``Bag.to_xml`` on the node's containing bag
    (or the wrapper-root bag for top-level rendering) and forward
    the result to finalize.
    """

    def render(
        self,
        source: Any,
        *,
        pretty: bool = False,
        doc_header: bool | str | None = None,
        **_opts: Any,
    ) -> str:
        """Override the universal walk: XML reuses ``Bag.to_xml``.

        Accepts a Bag (serialized directly) or a single BagNode
        (wrapped in an ephemeral Bag so indentation and doc_header
        match the legacy ``render_xml`` behavior).
        """
        if isinstance(source, Bag):
            text = source.to_xml(pretty=pretty, doc_header=doc_header)
        else:
            node = source
            tag = node.node_tag or node.label
            wrapper = Bag()
            wrapper.set_item(tag, node.value, _attributes=dict(node.attr or {}))
            text = wrapper.to_xml(pretty=pretty, doc_header=doc_header)
        assert text is not None
        return text

    def _format_attrs(self, attrs: dict[str, Any]) -> str:
        if not attrs:
            return ""
        parts = []
        for name, value in attrs.items():
            parts.append(f' {name}="{self._escape_attr(value)}"')
        return "".join(parts)
