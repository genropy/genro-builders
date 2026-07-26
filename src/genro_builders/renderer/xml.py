# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""XmlRenderer — the shared ``xml`` render mode.

Rides the universal walk on ``RendererBase``: pointers resolved,
framework markers filtered, each node composed via ``rendered_item``.
Exposed by ``BuilderBase.renderer_xml`` so every dialect serves
``xml`` without declaring its own renderer.
"""

from __future__ import annotations

from typing import Any

from .base import RendererBase


class XmlRenderer(RendererBase):
    """Renderer of the shared ``xml`` mode.

    Exposed by ``BuilderBase.renderer_xml`` so every dialect can
    serve ``xml`` without declaring its own renderer. Concrete dialects
    that want a custom XML walk override ``renderer_xml`` on their
    builder to return a different renderer class.

    A real render: it rides the universal walk on ``RendererBase`` (so
    pointers are resolved and framework markers filtered out, like every
    other dialect) and composes each node via ``rendered_item``. The raw
    structural view of the source — markers and unresolved pointers
    included — is a different thing entirely: call ``source.to_xml()``
    on the bag directly.
    """

    mode = "xml"

    def rendered_item(
        self,
        node: Any,
        item: Any,
        runtime_attrs: dict[str, Any],
        *,
        tag: str,
        pretty: bool = False,
        depth_offset: int = 0,
        **_opts: Any,
    ) -> str:
        """Emit the XML fragment for ``node``.

        - ``tag``/``runtime_attrs`` are already resolved by the base
          ``_handle_meta`` (render_tag and render_attributes applied).
        - ``item`` is a list of already-rendered child fragments when
          the node's value is a Bag; a leaf value otherwise (``None``
          for empty leaves).
        - XML has no void tags: a childless, textless element is
          ``<tag></tag>``.
        - ``pretty`` indents by wrapper-rooted depth, one node per line;
          ``depth_offset`` shifts it for the nodes of a component
          expansion, whose own root sits at 0.
        """
        attrs = self._format_attrs(runtime_attrs)
        indent = "  " * self._node_depth(node, depth_offset) if pretty else ""
        newline = "\n" if pretty else ""
        if isinstance(item, list):
            body = "".join(item)
            return f"{indent}<{tag}{attrs}>{newline}{body}{indent}</{tag}>{newline}"
        if item is None:
            return f"{indent}<{tag}{attrs}></{tag}>{newline}"
        return f"{indent}<{tag}{attrs}>{self._escape_text(item)}</{tag}>{newline}"

    def finalize(
        self,
        result: Any,
        target: Any,
        *,
        doc_header: bool | str | None = None,
        **opts: Any,
    ) -> Any:
        """Join fragments, optionally prepend an XML declaration, then
        consume ``target`` via the base ``finalize``.

        ``doc_header=True`` prepends the standard declaration; a string
        is prepended verbatim. The document-level header belongs here,
        not in ``rendered_item`` (which is per-node).
        """
        if isinstance(result, list):
            result = "".join(result)
        if doc_header is True:
            result = "<?xml version='1.0' encoding='UTF-8'?>" + result
        elif isinstance(doc_header, str):
            result = doc_header + result
        # ``opts`` (e.g. ``pretty``) are per-node walk options already
        # consumed in ``rendered_item``; the base finalize only handles
        # result + target, so they are absorbed here, not forwarded.
        return super().finalize(result, target)

    def _format_attrs(self, attrs: dict[str, Any]) -> str:
        if not attrs:
            return ""
        parts = []
        for name, value in attrs.items():
            # ``xmlns_<prefix>`` is the author form of a namespace
            # declaration (Python attribute names cannot carry a colon);
            # it surfaces as ``xmlns:<prefix>``. No other underscore is
            # rewritten — XML attribute names are emitted verbatim.
            out_name = (
                "xmlns:" + name[len("xmlns_"):]
                if name.startswith("xmlns_")
                else name
            )
            parts.append(f' {out_name}="{self._escape_attr(value)}"')
        return "".join(parts)
