# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""SvgBuilder and SvgRenderer — SVG document builder and renderer.

Provides a domain-specific grammar for building SVG documents with
validation. The schema covers structural, shape, text, gradient,
filter, animation, and descriptive elements from the W3C SVG spec.

Attribute naming: SVG uses kebab-case (``stroke-width``) but Python
requires identifiers, so pass ``stroke_width`` — the renderer converts
underscores to hyphens for known presentation attributes.

Example:
    Creating an SVG document::

        from genro_builders.contrib.svg import SvgBuilder

        builder = SvgBuilder()
        svg = builder.source.svg(width="200", height="200", viewBox="0 0 200 200")
        svg.rect(x="10", y="10", width="80", height="80", fill="steelblue")
        svg.circle(cx="150", cy="50", r="40", fill="coral")
        svg.text("Hello SVG", x="100", y="150", text_anchor="middle")

        builder.build()
        print(builder.render())
"""

from __future__ import annotations

from typing import Any

from genro_bag import Bag, BagNode

from ...builder import BagBuilderBase
from ...renderer import BagRendererBase
from .svg_elements import SvgElements

# Presentation attributes that use kebab-case in SVG.
# Underscores in these attribute names are converted to hyphens.
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

# Void elements (self-closing in SVG)
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
    """Renderer for SVG documents."""

    def render(self, built_bag: Bag, output: Any = None) -> str:
        """Render the built Bag to SVG string."""
        lines = []
        for node in built_bag:
            lines.append(self._node_to_svg(node, indent=0))
        return "\n".join(lines)

    def _node_to_svg(self, node: BagNode, indent: int = 0) -> str:
        """Recursively convert a node to SVG markup."""
        tag = node.node_tag or node.label
        attrs = " ".join(
            _render_attr(k, v)
            for k, v in node.attr.items()
            if not k.startswith("_")
        )
        attrs_str = f" {attrs}" if attrs else ""
        spaces = "  " * indent

        node_value = node.get_value(static=True)
        is_leaf = not isinstance(node_value, Bag)

        if is_leaf:
            if tag in _VOID_TAGS and (node_value is None or node_value == ""):
                return f"{spaces}<{tag}{attrs_str} />"
            content = "" if node_value is None else str(node_value)
            return f"{spaces}<{tag}{attrs_str}>{content}</{tag}>"

        lines = [f"{spaces}<{tag}{attrs_str}>"]
        for child in node_value:
            lines.append(self._node_to_svg(child, indent + 1))
        lines.append(f"{spaces}</{tag}>")
        return "\n".join(lines)


class SvgBuilder(BagBuilderBase, SvgElements):
    """Builder for SVG documents.

    All SVG elements are defined as @element methods in SvgElements mixin.
    Attribute underscores are converted to hyphens for SVG presentation
    attributes (e.g., ``stroke_width`` becomes ``stroke-width``).

    Example:
        >>> from genro_builders.contrib.svg import SvgBuilder
        >>> builder = SvgBuilder()
        >>> svg = builder.source.svg(width="100", height="100")
        >>> svg.circle(cx="50", cy="50", r="40", fill="red")
        >>> builder.build()
        >>> print(builder.render())
    """

    _renderers = {"svg": SvgRenderer}
