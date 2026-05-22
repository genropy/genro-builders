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

    def __init__(self, handler: Any, builder: Any = None) -> None:
        self.handler = handler
        # When ``builder`` is None (default) the renderer is bound to
        # the handler's primary dialect — used by ``handler.renderer``.
        # When a sub-renderer is instantiated via
        # ``handler.renderer_for(sub_builder)`` the explicit ``builder``
        # locks the renderer to that dialect, so polymorphic dispatch
        # via ``node._builder`` can compare against it without looping.
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

    def _render_subtree(self, node: Any, emit: Any) -> None:
        """Render a single node-and-descendants into ``emit``.

        Default entry point invoked by a host renderer when it delegates
        a sub-builder subtree (decision 2, P5). Subclasses with extra
        per-walk parameters (HTML's ``xml``/``pretty``/``depth``, etc.)
        override this to forward sensible defaults to their own
        ``_render_node`` signature.

        Default implementation assumes ``_render_node(node, emit)`` has
        no extra kwargs (matches the bare ``RendererBase``, ``SvgRenderer``,
        ``CssRenderer`` shapes).
        """
        self._render_node(node, emit)  # type: ignore[attr-defined]

    def _render_subbuilder(
        self,
        node: Any,
        emit: Any,
        node_builder: Any,
        **walk_kwargs: Any,
    ) -> None:
        """Delegate a sub-builder subtree, optionally wrapping the
        sub-renderer output in a host-dialect tag.

        The wrap tag (and any framework-emitted attribute on it) is
        declared on the host schema by the ``@subbuilder(..., wrap_tag=...)``
        decorator. The standard example is the SVG ``html`` subbuilder
        wrapped in ``<foreignObject xmlns="http://www.w3.org/1999/xhtml">``:
        the user only writes ``svg.html().div(...)`` while the runtime
        emits the foreignObject envelope that replaces the bare ``html``
        node so the markup satisfies the SVG embedding rule.

        When ``wrap_tag`` is set the subbuilder node itself is invisible
        in the output: the wrap tag stands in for it and the
        sub-renderer is asked to render only the children. Without a
        wrap tag the sub-renderer renders the subbuilder node verbatim
        (HTML hosting SVG: the ``<svg>`` tag is part of HTML5 and must
        be emitted).
        """
        sub_renderer = self.handler.renderer_for(node_builder)
        wrap_tag = node.attr.get("_wrap_tag")
        if not wrap_tag:
            sub_renderer._render_subtree(node, emit)
            return
        # The wrap tag stands in for the subbuilder node, so the user
        # attributes on that node (e.g. ``x=10, y=20`` for
        # ``svg.html(x=10, y=20)``) belong on the wrap tag. We format
        # them with the host renderer (the wrap tag is part of the host
        # dialect) and prepend the framework-emitted wrap attributes
        # (e.g. xmlns) so well-formedness is guaranteed.
        user_attrs = self._format_attrs(node.attr)  # type: ignore[attr-defined]
        wrap_attrs = self._wrap_attrs_for(node_builder)
        emit(f"<{wrap_tag}{wrap_attrs}{user_attrs}>")
        value = node.value
        if isinstance(value, Bag):
            for child in value:
                sub_renderer._render_subtree(child, emit)
        elif value is not None:
            emit(sub_renderer._escape_text(value))
        emit(f"</{wrap_tag}>")

    def _wrap_attrs_for(self, node_builder: Any) -> str:
        """Hook returning the attributes emitted on the wrap tag.

        For the HTML re-entry inside SVG the XML spec calls for
        ``xmlns="http://www.w3.org/1999/xhtml"`` on the first HTML
        node; the framework places it on the wrap tag
        (``<foreignObject>``) so the result is XML well-formed. Hosts
        whose embedding rule is different can override this hook.
        """
        if getattr(node_builder, "_name", None) == "html":
            return ' xmlns="http://www.w3.org/1999/xhtml"'
        return ""

    def render_xml(
        self,
        source: Bag,
        render_target: Any = None,
        *,
        pretty: bool = False,
    ) -> str | None:
        """Default XML render: ``Bag.to_xml(pretty=...)`` then routed
        to render_target if provided."""
        text = source.to_xml(pretty=pretty)
        return self._write_or_return(text, render_target)

    def _write_or_return(self, text: str | None, render_target: Any) -> str | None:
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
            path.write_text(text or "", encoding="utf-8")
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
