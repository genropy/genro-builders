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

import textwrap
from typing import Any

from genro_bag import BagNode

from ...builder import BagBuilderBase
from ...renderer import CTX_KEYS, BagRendererBase
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
    """Renderer for SVG documents.

    Uses the base class walk/dispatch/resolve infrastructure.
    Only render_node is overridden to produce SVG markup.
    """

    def render_node(
        self, node: BagNode, ctx: dict[str, Any],
        template: str | None = None, **kwargs: Any,
    ) -> str | None:
        """Render a single node as SVG markup."""
        tag = node.node_tag or node.label
        attrs = " ".join(
            _render_attr(k, v)
            for k, v in ctx.items()
            if not k.startswith("_") and k not in CTX_KEYS
        )
        attrs_str = f" {attrs}" if attrs else ""

        node_value = ctx["node_value"]
        children = ctx["children"]

        if not children:
            if tag in _VOID_TAGS and not node_value:
                return f"<{tag}{attrs_str} />"
            content = node_value or ""
            return f"<{tag}{attrs_str}>{content}</{tag}>"

        indented = textwrap.indent(children, "  ")
        return f"<{tag}{attrs_str}>\n{indented}\n</{tag}>"


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
