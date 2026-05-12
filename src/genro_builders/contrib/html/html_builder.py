# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""HtmlBuilder — HTML5 dialect for genro-builders.

Pairs the dialect grammar from ``Html5Elements`` (generated from the
W3C RELAX NG schema) with a linear ``render_html`` mode. Void tags are
serialized self-closing XHTML-style (``<img src="x"/>``). Attribute
values of type ``True``/``False``/``None`` are emitted as JS literals
(``"true"``, ``"false"``, ``"null"``) so the JS layer can consume the
three-state semantics directly.
"""

from __future__ import annotations

from typing import Any

from genro_bag import Bag

from ...builder import BagBuilderBase
from .html5_elements import Html5Elements


_ATTR_MAP = {"_class": "class", "_for": "for"}

_VOID_TAGS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img",
    "input", "link", "meta", "source", "track", "wbr",
})

_TEXT_ESCAPE = str.maketrans({"&": "&amp;", "<": "&lt;", ">": "&gt;"})
_ATTR_ESCAPE = str.maketrans(
    {"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"},
)


class HtmlBuilder(BagBuilderBase, Html5Elements):
    """HTML5 dialect builder. Renders the built bag as linear HTML."""

    _default_render_mode = "html"

    def render_html(
        self,
        built: Bag,
        render_target: Any = None,
        *,
        xml: bool = True,
        pretty: bool = False,
    ) -> str | None:
        """Serialize ``built`` as HTML5 markup.

        Returns the rendered string when ``render_target`` is ``None``;
        otherwise writes/calls into the target and returns ``None``.

        ``xml=True`` (default) emits void tags self-closing
        XHTML-style (``<img src="x"/>``) so the document is also XML
        well-formed — useful when SVG/XML pipelines consume the
        output. ``xml=False`` emits idiomatic HTML5 (``<img src="x">``).

        ``pretty=True`` emits multi-line indented output (2 spaces per
        level). An element whose only child is text stays on a single
        line (``<p>Hello</p>``); element children move to their own
        lines. The output ends with a trailing newline. ``pretty=False``
        (default) emits a single linear string with no whitespace
        added.
        """
        chunks: list[str] = []
        for node in built:
            self._render_node(node, chunks.append, xml=xml, pretty=pretty, depth=0)
        text = "".join(chunks)
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

    def _render_node(
        self,
        node: Any,
        emit: Any,
        *,
        xml: bool,
        pretty: bool,
        depth: int,
    ) -> None:
        tag = node.node_tag or node.label
        attrs = self._format_attrs(node.attr)
        indent = "  " * depth if pretty else ""
        newline = "\n" if pretty else ""
        if tag in _VOID_TAGS:
            emit(f"{indent}<{tag}{attrs}/>{newline}" if xml else f"{indent}<{tag}{attrs}>{newline}")
            return
        value = node.value
        if isinstance(value, Bag):
            emit(f"{indent}<{tag}{attrs}>{newline}")
            for child in value:
                self._render_node(
                    child, emit, xml=xml, pretty=pretty, depth=depth + 1,
                )
            emit(f"{indent}</{tag}>{newline}")
        elif value is not None:
            emit(
                f"{indent}<{tag}{attrs}>"
                f"{str(value).translate(_TEXT_ESCAPE)}"
                f"</{tag}>{newline}"
            )
        else:
            emit(f"{indent}<{tag}{attrs}></{tag}>{newline}")

    def _format_attrs(self, attrs: dict[str, Any]) -> str:
        parts: list[str] = []
        for raw_name, value in attrs.items():
            if raw_name.startswith("_") and raw_name not in _ATTR_MAP:
                continue
            name = _ATTR_MAP.get(raw_name, raw_name)
            if value is True:
                rendered = "true"
            elif value is False:
                rendered = "false"
            elif value is None:
                rendered = "null"
            else:
                rendered = str(value).translate(_ATTR_ESCAPE)
            parts.append(f' {name}="{rendered}"')
        return "".join(parts)
