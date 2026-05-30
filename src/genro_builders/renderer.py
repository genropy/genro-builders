# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""RendererBase — base class for builder renderers.

A renderer walks a source bag and produces a textual representation.
Each dialect declares its own renderer subclass (``HtmlRenderer``,
``SvgRenderer``, ...) and exposes one or more ``render_<mode>``
methods. ``render()`` dispatches to the requested mode, filtering
kwargs against the method's signature so that mode-specific options
do not leak across modes.

Renderer instances are owned by the ``BuilderHandler``, one per
mode, lazy and cached (decision 6 of the contract, v0.4.0). The
property ``handler.renderer`` returns the renderer for the default
mode; ``handler.render(...)`` dispatches to the requested mode and
forwards to ``self._get_renderer(mode).render(...)``.

Decision 8 (v0.4.0): rendering lives in dedicated classes parallel
to the builder; the builder only declares grammar.
"""

from __future__ import annotations

import inspect
from pathlib import Path
from typing import Any

from genro_bag import Bag

_TEXT_ESCAPE = str.maketrans({"&": "&amp;", "<": "&lt;", ">": "&gt;"})
_ATTR_ESCAPE = str.maketrans(
    {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"},
)


class RendererBase:
    """Base renderer. Concrete dialects subclass it and add
    ``render_<mode>`` methods."""

    def __init__(self, handler: Any = None, builder: Any = None) -> None:
        self.handler = handler
        # When ``builder`` is None (default) the renderer is bound to
        # the handler's primary dialect — used by ``handler.renderer``.
        # When a sub-renderer is instantiated via
        # ``handler.renderer_for(sub_builder)`` the explicit ``builder``
        # locks the renderer to that dialect, so polymorphic dispatch
        # via ``node._builder`` can compare against it without looping.
        #
        # ``handler`` is optional during step 2a of the renderer-side
        # chain refactor: the builder property ``renderer_<mode>`` can
        # produce an instance carrying only the builder; the caller
        # (typically the handler) injects ``self.handler`` right after.
        self._builder = builder

    @property
    def builder(self) -> Any:
        return self._builder if self._builder is not None else self.handler.builder

    def render(
        self,
        source: Bag,
        mode: str | None = None,
        render_target: Any = None,
        **kwargs: Any,
    ) -> Any:
        """Dispatch to the requested render mode.

        ``mode is None`` -> the dialect's default mode (class attribute
        ``_default_render_mode`` on the builder).

        ``**kwargs`` are mode-specific options. The dispatch filters
        them against the target method's signature: kwargs the method
        does not declare are silently ignored.
        """
        effective_mode = mode if mode is not None else self.builder._default_render_mode
        method_name = f"render_{effective_mode}"
        method = None
        for klass in type(self).__mro__:
            if method_name in klass.__dict__:
                method = klass.__dict__[method_name]
                break
        if method is None:
            raise ValueError(
                f"{type(self).__name__} does not support render mode "
                f"'{effective_mode}' (no method '{method_name}')",
            )
        accepted = {
            p for p in inspect.signature(method).parameters
            if p not in {"self", "source", "render_target"}
        }
        filtered = {k: v for k, v in kwargs.items() if k in accepted}
        return method(self, source, render_target=render_target, **filtered)

    def _render_node(self, node: Any, emit: Any, **walk_kwargs: Any) -> None:
        """Hook for concrete renderers that walk the source tree.

        Concrete renderers that act as hosts of subbuilders, or that
        drive their own walk inside ``render_<mode>``, must override
        this to emit the markup of ``node`` plus its descendants.
        ``RendererBase`` does not walk the tree on its own.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not implement _render_node; "
            "override it to emit markup for the node and its descendants",
        )

    def _format_attrs(self, attrs: dict[str, Any]) -> str:
        """Hook for concrete renderers that format per-node attributes.

        Concrete renderers that host subbuilders with ``wrap_tag`` must
        override this to format the user attributes of the wrapper node
        in the host dialect. ``RendererBase`` does not format attributes
        on its own.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not implement _format_attrs; "
            "override it to format attributes for the host dialect",
        )

    def _render_subtree(self, node: Any, emit: Any) -> None:
        """Render a single node-and-descendants into ``emit``.

        Default entry point invoked by a host renderer when it delegates
        a sub-builder subtree (decision 2, P5). Subclasses with extra
        per-walk parameters (HTML's ``xml``/``pretty``/``depth``, etc.)
        override this to forward sensible defaults to their own
        ``_render_node`` signature.

        Default implementation assumes ``_render_node(node, emit)`` has
        no extra kwargs (matches ``SvgRenderer`` and ``CssRenderer``
        shapes).
        """
        self._render_node(node, emit)

    def _render_subbuilder(
        self,
        node: Any,
        emit: Any,
        node_builder: Any,
        **walk_kwargs: Any,
    ) -> None:
        """Delegate a sub-builder subtree, optionally wrapping the
        sub-renderer output in a host-dialect envelope.

        The host builder declares how it embeds a given sub-dialect via
        a ``wrapper_<sub_name>`` method returning a dict
        ``{"tag": <host-side wrap tag>, "attrs": <framework attrs>}``.
        Example: ``SvgExtensions.wrapper_html`` returns
        ``{"tag": "foreignObject", "attrs": {"xmlns": ".../xhtml"}}``,
        which the runtime emits around the children of an
        ``svg.html(...)`` subtree to satisfy the SVG embedding rule.

        When a wrapper is declared the subbuilder node itself is invisible
        in the output: the wrap tag stands in for it and the
        sub-renderer is asked to render only the children. Without a
        wrapper the sub-renderer renders the subbuilder node verbatim
        (HTML hosting SVG: the ``<svg>`` tag is part of HTML5 and must
        be emitted).
        """
        sub_renderer = self.handler.renderer_for(node_builder)
        wrapper_spec = self._wrapper_spec_for(node_builder)
        if wrapper_spec is None:
            sub_renderer._render_subtree(node, emit)
            return
        # The wrap tag stands in for the subbuilder node, so the user
        # attributes on that node (e.g. ``x=10, y=20`` for
        # ``svg.html(x=10, y=20)``) belong on the wrap tag. We format
        # them with the host renderer (the wrap tag is part of the host
        # dialect) and prepend the framework-emitted wrap attributes
        # (e.g. xmlns) so well-formedness is guaranteed.
        wrap_tag = wrapper_spec["tag"]
        wrap_attrs = wrapper_spec.get("attrs") or {}
        user_attrs = self._format_attrs(node.attr)
        framework_attrs = self._format_attrs(wrap_attrs)
        emit(f"<{wrap_tag}{framework_attrs}{user_attrs}>")
        value = node.value
        if isinstance(value, Bag):
            for child in value:
                sub_renderer._render_subtree(child, emit)
        elif value is not None:
            emit(sub_renderer._escape_text(value))
        emit(f"</{wrap_tag}>")

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

    def _write_or_return(self, text: str, render_target: Any) -> str | None:
        """Common pattern: return string, write to filesystem path, file-like, or invoke callable.

        Accepted ``render_target`` shapes:

        - ``None`` → return the text;
        - ``str`` or ``pathlib.Path`` → treat as filesystem path, create parent
          directories if missing, write text with UTF-8 encoding;
        - object with ``.write`` callable → write to file-like;
        - plain callable → invoke with the text.
        """
        if render_target is None:
            return text
        if isinstance(render_target, (str, Path)):
            path = Path(render_target)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            return None
        write = getattr(render_target, "write", None)
        if callable(write):
            write(text)
            return None
        if callable(render_target):
            render_target(text)
            return None
        raise TypeError(
            f"render_target {render_target!r} is neither a path "
            "(str/Path), writable (.write), nor callable",
        )

    def _escape_text(self, value: Any) -> str:
        """Escape a text value for safe inclusion in XML/HTML body."""
        return str(value).translate(_TEXT_ESCAPE)

    def _escape_attr(self, value: Any) -> str:
        """Escape an attribute value (also escapes double quotes)."""
        return str(value).translate(_ATTR_ESCAPE)


class XmlRenderer(RendererBase):
    """Renderer of the shared ``xml`` mode.

    Exposed by ``BagBuilderBase.renderer_xml`` so every dialect can
    serve ``xml`` without declaring its own renderer. Concrete dialects
    that want a custom XML walk override ``renderer_xml`` on their
    builder to return a different renderer class.
    """

    def render_xml(
        self,
        source: Bag,
        render_target: Any = None,
        *,
        pretty: bool = False,
        doc_header: bool | str | None = None,
    ) -> str | None:
        """Serialize ``source`` as XML via ``Bag.to_xml``.

        - ``pretty`` formats with indentation;
        - ``doc_header`` is forwarded verbatim: ``True`` emits the
          standard ``<?xml version='1.0' encoding='UTF-8'?>`` declaration,
          a string is prepended verbatim, ``False``/``None`` omit it.
        """
        text = source.to_xml(pretty=pretty, doc_header=doc_header)
        assert text is not None  # to_xml returns None only with filename=
        return self._write_or_return(text, render_target)
