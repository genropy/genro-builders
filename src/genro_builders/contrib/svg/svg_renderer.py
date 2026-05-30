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

from genro_bag import Bag

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
    """Renderer for the SVG dialect (one mode: ``render_svg``)."""

    def render_svg(self, source: Bag, render_target: Any = None) -> str | None:
        """Serialize ``source`` as SVG markup. See module docstring."""
        chunks: list[str] = []
        for node in source:
            self._render_node(node, chunks.append)
        text = "".join(chunks)
        return self._write_or_return(text, render_target)

    def _render_node(self, node: Any, emit: Any) -> None:
        # @subbuilder polymorphism (decision 2, P5/P6): delegate any
        # foreign-dialect subtree to the appropriate renderer. If the
        # host schema declares a wrap_tag (e.g. SVG html-subbuilder
        # wrapped in foreignObject) the host emits the envelope while
        # the sub-renderer fills the body. ``node.builder`` resolves
        # slot + ancestor walk.
        node_builder = node.builder
        if node_builder is not None and node_builder is not self.builder:
            self._render_subbuilder(node, emit, node_builder)
            return
        tag = node.node_tag or node.label
        attrs = self._format_attrs(node.attr)
        if tag in _VOID_TAGS:
            emit(f"<{tag}{attrs} />")
            return
        emit(f"<{tag}{attrs}>")
        value = node.value
        if isinstance(value, Bag):
            for child in value:
                self._render_node(child, emit)
        elif value is not None:
            emit(self._escape_text(value))
        emit(f"</{tag}>")

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
