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

from .builder_bag import BuilderBag, BuilderBagNode

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

    def render_old(self, source: Any, **opts: Any) -> Any:
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
            raise RuntimeError(f"render() got a Bag: {type(source).__name__}")
        node = source
        # Data-elements are transparent to every renderer: they carry data
        # infrastructure (write/compute/side-effect), not markup.
        if node.attr.get("_is_data_element"):
            return ""
        node_builder = node.builder
        if node_builder is not self.builder:
            # Foreign builder: hand off to its renderer.
            rn = self.get_render(node_builder)
            wrapper_spec = self._wrapper_spec_for(node_builder)
            if wrapper_spec is None:
                # No envelope: the sub-builder node renders verbatim.
                return rn.render_old(node, **opts)
            # Envelope: the wrap tag replaces the sub-builder node, the
            # sub-renderer emits only the children.
            value = node.value
            if isinstance(value, Bag):
                children_fragment = "".join(rn.render_old(child, **opts) for child in value)
            elif value is None:
                children_fragment = ""
            else:
                children_fragment = rn._escape_text(value)
            return self._wrap_fragment(node, children_fragment, wrapper_spec)
        item, ra = node.runtime_values()
        if isinstance(node.value, BuilderBag):
            item = [self.render_old(child, **opts) for child in node.value]
        return self.rendered_item(node, item, ra, **opts)

    def render(self, node: Any, **opts: Any) -> Any:
        """Walk a node and produce its rendered fragment.

        Receives a BagNode and only a BagNode; anything else is a caller
        error (the caller resolves the bag/node discontinuity, not the
        renderer). Data-elements are transparent — they return ``None``
        (the walk never emits strings, so absence of output is ``None``,
        not ``""``). For a node whose value is a structural BuilderBag the
        children are rendered recursively into a nested list (``None``
        fragments from transparent children are dropped); the dialect's
        ``rendered_item`` then composes the fragment.

        Sub-builders are not handled yet — reintroduced after the compose
        refactoring.
        """
        if not isinstance(node, BuilderBagNode):
            raise TypeError(
                f"render() requires a BuilderBagNode, got {type(node).__name__}",
            )
        if node.attr.get("_is_data_element"):
            return None
        item, ra = node.runtime_values()
        if isinstance(node.value, BuilderBag):
            item = self.render_children(node.value, **opts)
        return self.rendered_item(node, item, ra, **opts)

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

    def finalize(self, result: Any, target: Any) -> Any:
        """Turn the render result into the user-visible output.

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

    mode = "xml"

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
