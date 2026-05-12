# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""RendererBase — base class for builder renderers.

A renderer walks a built bag and produces a textual representation.
Each dialect declares its own renderer subclass (``HtmlRenderer``,
``SvgRenderer``, ...) and exposes one or more ``render_<mode>``
methods. ``render()`` dispatches to the requested mode, filtering
kwargs against the method's signature so that mode-specific options
do not leak across modes.

The renderer is owned by the ``BuilderHandler`` (one per handler,
lazy, cached) and accessible as ``handler.renderer``. The shortcut
``handler.render(...)`` forwards to ``self.renderer.render(...)``.

Decision 8 (renegotiated 2026-05-12): rendering and compilation live
in dedicated classes parallel to the builder; the builder only
declares grammar.
"""

from __future__ import annotations

import inspect
from typing import Any

from genro_bag import Bag


_TEXT_ESCAPE = str.maketrans({"&": "&amp;", "<": "&lt;", ">": "&gt;"})
_ATTR_ESCAPE = str.maketrans(
    {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"},
)


class RendererBase:
    """Base renderer. Concrete dialects subclass it and add
    ``render_<mode>`` methods."""

    def __init__(self, handler: Any) -> None:
        self.handler = handler

    @property
    def builder(self) -> Any:
        return self.handler.builder

    def render(
        self,
        built: Bag,
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
            if p not in {"self", "built", "render_target"}
        }
        filtered = {k: v for k, v in kwargs.items() if k in accepted}
        return method(self, built, render_target=render_target, **filtered)

    def render_xml(
        self,
        built: Bag,
        render_target: Any = None,
        *,
        pretty: bool = False,
    ) -> str | None:
        """Default XML render: ``Bag.to_xml(pretty=...)`` then routed
        to render_target if provided."""
        text = built.to_xml(pretty=pretty)
        return self._write_or_return(text, render_target)

    def _write_or_return(self, text: str | None, render_target: Any) -> str | None:
        """Common pattern: return string, write to file-like, or invoke callable."""
        if render_target is None:
            return text
        write = getattr(render_target, "write", None)
        if callable(write):
            write(text)
            return None
        if callable(render_target):
            render_target(text)
            return None
        raise TypeError(
            f"render_target {render_target!r} is neither writable "
            "(.write) nor callable",
        )

    def _escape_text(self, value: Any) -> str:
        """Escape a text value for safe inclusion in XML/HTML body."""
        return str(value).translate(_TEXT_ESCAPE)

    def _escape_attr(self, value: Any) -> str:
        """Escape an attribute value (also escapes double quotes)."""
        return str(value).translate(_ATTR_ESCAPE)
