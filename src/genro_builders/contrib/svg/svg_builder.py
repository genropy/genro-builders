# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""SvgBuilder and SvgRenderer — SVG document builder and renderer."""

from __future__ import annotations

from typing import Any

from genro_bag import Bag, BagNode

from ...builder import BagBuilderBase
from ...renderer import CTX_KEYS, BagRendererBase, RenderNode
from .svg_elements import SvgElements

# Presentation attributes that use kebab-case in SVG.
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


def _render_attr(key: str, value: Any) -> str:
    """Render a single attribute, converting underscore to kebab where needed."""
    if key in _KEBAB_ATTRS:
        key = key.replace("_", "-")
    elif key == "class_":
        key = "class"
    return f'{key}="{value}"'


class SvgRenderer(BagRendererBase):
    """Renderer for SVG documents.

    Top-down: render_node returns a RenderNode for containers
    or a plain string for leaves. Reads from node.runtime_attrs.
    """

    def render_node(
        self, node: BagNode,
        parent: list | None = None, **kwargs: Any,
    ) -> str | RenderNode | None:
        """Render a single node as SVG markup."""
        tag = node.node_tag or node.label
        attrs = node.runtime_attrs
        attrs_str_parts = [
            _render_attr(k, v)
            for k, v in attrs.items()
            if not k.startswith("_") and k not in CTX_KEYS
        ]
        attrs_str = f" {' '.join(attrs_str_parts)}" if attrs_str_parts else ""

        value = node.runtime_value
        node_value = "" if value is None or isinstance(value, Bag) else str(value)
        has_children = isinstance(node.get_value(static=True), Bag)

        if has_children:
            return RenderNode(
                before=f"<{tag}{attrs_str}>",
                after=f"</{tag}>",
                value=node_value,
                indent="  ",
            )

        if tag in _VOID_TAGS and not node_value:
            return f"<{tag}{attrs_str} />"
        content = node_value or ""
        return f"<{tag}{attrs_str}>{content}</{tag}>"


class SvgBuilder(BagBuilderBase, SvgElements):
    """Builder for SVG documents."""

    _renderers = {"svg": SvgRenderer}
