# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""SvgRenderer — renderer for the SVG dialect.

Walks a source bag and produces SVG markup. SVG is XML by definition,
so void tags are always self-closing; the legacy style ``<rect />``
(space before the slash, per W3C XHTML convention followed by SVG
tools) is preserved.

Attribute names use kebab-case in SVG (``stroke-width``) but Python
identifiers can't contain hyphens. The renderer rewrites underscore
attributes listed in ``_KEBAB_ATTRS`` to their hyphenated form
(``stroke_width`` → ``stroke-width``). ``_class`` / ``_for`` map to
``class`` / ``for`` like in HTML.
"""

from __future__ import annotations

from typing import Any

from ...renderer import RendererBase

_ATTR_MAP = {"_class": "class", "_for": "for"}

_KEBAB_ATTRS = frozenset({
    "alignment_baseline", "baseline_shift", "clip_path", "clip_rule",
    "color_interpolation", "color_interpolation_filters", "dominant_baseline",
    "fill_opacity", "fill_rule", "flood_color", "flood_opacity",
    "font_family", "font_size", "font_size_adjust", "font_stretch",
    "font_style", "font_variant", "font_weight", "glyph_orientation_horizontal",
    "glyph_orientation_vertical", "image_rendering", "letter_spacing",
    "lighting_color", "marker_end", "marker_mid", "marker_start",
    "overline_position", "overline_thickness", "paint_order",
    "pointer_events", "shape_rendering", "stop_color", "stop_opacity",
    "strikethrough_position", "strikethrough_thickness", "stroke_dasharray",
    "stroke_dashoffset", "stroke_linecap", "stroke_linejoin",
    "stroke_miterlimit", "stroke_opacity", "stroke_width",
    "text_anchor", "text_decoration", "text_rendering",
    "underline_position", "underline_thickness", "unicode_bidi",
    "word_spacing", "writing_mode",
})

_VOID_TAGS = frozenset({
    "animate", "animateMotion", "animateTransform", "circle",
    "ellipse", "feBlend", "feColorMatrix", "feComposite",
    "feConvolveMatrix", "feDiffuseLighting", "feDisplacementMap",
    "feDistantLight", "feDropShadow", "feFlood", "feGaussianBlur",
    "feImage", "feMergeNode", "feMorphology", "feOffset",
    "fePointLight", "feSpecularLighting", "feSpotLight", "feTile",
    "feTurbulence", "image", "line", "metadata", "path", "polygon",
    "polyline", "rect", "set", "stop", "use",
})


class SvgRenderer(RendererBase):
    """Renderer for the SVG dialect.

    ``rendered_item`` emits the markup for one node. The walk is
    driven by the universal ``RendererBase.render`` on the base
    class: children fragments arrive already-rendered via ``item``.
    """

    def rendered_item(
        self,
        node: Any,
        item: Any,
        runtime_attrs: dict[str, Any],
        **_opts: Any,
    ) -> str:
        """Emit the SVG fragment for ``node``.

        - ``item`` is a list of already-rendered child fragments when
          the node's value is a Bag; a leaf value otherwise (``None``
          for empty leaves).
        - Void tags use the XHTML-style self-closing form preferred
          by SVG tooling (``<rect ... />``).
        """
        tag = node.node_tag or node.label
        attrs = self._format_attrs(runtime_attrs)
        if tag in _VOID_TAGS:
            return f"<{tag}{attrs} />"
        if isinstance(item, list):
            return f"<{tag}{attrs}>{''.join(item)}</{tag}>"
        if item is None:
            return f"<{tag}{attrs}></{tag}>"
        return f"<{tag}{attrs}>{self._escape_text(item)}</{tag}>"

    def _format_attrs(self, attrs: dict[str, Any]) -> str:
        parts: list[str] = []
        for raw_name, value in attrs.items():
            if raw_name.startswith("_") and raw_name not in _ATTR_MAP:
                continue
            if raw_name in _ATTR_MAP:
                name = _ATTR_MAP[raw_name]
            elif raw_name in _KEBAB_ATTRS:
                name = raw_name.replace("_", "-")
            else:
                name = raw_name
            if value is True:
                rendered = "true"
            elif value is False:
                rendered = "false"
            elif value is None:
                rendered = "null"
            else:
                rendered = self._escape_attr(value)
            parts.append(f' {name}="{rendered}"')
        return "".join(parts)
