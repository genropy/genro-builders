# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for SvgBuilder — SVG document builder and renderer."""

import pytest

from genro_builders.contrib.svg import SvgBuilder


class TestSvgBuilderSchema:
    """SVG schema defines expected elements."""

    def test_shape_elements_in_schema(self):
        """Shape elements are registered."""
        builder = SvgBuilder()
        for tag in ("rect", "circle", "ellipse", "line", "path", "polygon", "polyline"):
            assert tag in builder

    def test_structural_elements_in_schema(self):
        """Structural containers are registered."""
        builder = SvgBuilder()
        for tag in ("svg", "g", "defs", "symbol", "use"):
            assert tag in builder

    def test_text_elements_in_schema(self):
        """Text elements are registered."""
        builder = SvgBuilder()
        for tag in ("text", "tspan", "textPath"):
            assert tag in builder

    def test_gradient_elements_in_schema(self):
        """Gradient and pattern elements are registered."""
        builder = SvgBuilder()
        for tag in ("linearGradient", "radialGradient", "stop", "pattern"):
            assert tag in builder

    def test_filter_elements_in_schema(self):
        """Filter elements are registered."""
        builder = SvgBuilder()
        for tag in ("filter", "feGaussianBlur", "feOffset", "feBlend", "feDropShadow"):
            assert tag in builder

    def test_animation_elements_in_schema(self):
        """Animation elements are registered."""
        builder = SvgBuilder()
        for tag in ("animate", "animateTransform", "animateMotion", "set"):
            assert tag in builder


class TestSvgBuilderSource:
    """Source population works correctly."""

    def test_basic_shapes(self):
        """Create basic shapes in source."""
        builder = SvgBuilder()
        svg = builder.source.svg(width="200", height="200")
        svg.rect(x="10", y="10", width="80", height="80")
        svg.circle(cx="150", cy="50", r="40")

        assert len(svg.value) == 2

    def test_nested_groups(self):
        """Groups contain children."""
        builder = SvgBuilder()
        svg = builder.source.svg(width="100", height="100")
        g = svg.g(transform="translate(10,10)")
        g.rect(width="50", height="50")
        g.circle(cx="25", cy="25", r="10")

        assert len(g.value) == 2

    def test_defs_with_gradient(self):
        """Defs contain gradient definitions."""
        builder = SvgBuilder()
        svg = builder.source.svg(width="100", height="100")
        defs = svg.defs()
        grad = defs.linearGradient(id="grad1")
        grad.stop(offset="0%", stop_color="red")
        grad.stop(offset="100%", stop_color="blue")

        assert len(grad.value) == 2

    def test_text_with_tspan(self):
        """Text contains tspan children."""
        builder = SvgBuilder()
        svg = builder.source.svg(width="200", height="100")
        t = svg.text("Hello ", x="10", y="50")
        t.tspan("World", font_weight="bold")

        assert len(t.value) == 1

    def test_filter_chain(self):
        """Filter contains filter primitives."""
        builder = SvgBuilder()
        svg = builder.source.svg(width="100", height="100")
        defs = svg.defs()
        f = defs.filter(id="shadow")
        f.feGaussianBlur(stdDeviation="3", result="blur")
        f.feOffset(dx="2", dy="2", result="offsetBlur")
        f.feBlend(in_="SourceGraphic", in2="offsetBlur")

        assert len(f.value) == 3

    def test_leaf_rejects_children(self):
        """Leaf elements (shapes) reject children."""
        builder = SvgBuilder()
        svg = builder.source.svg(width="100", height="100")
        r = svg.rect(width="50", height="50")

        with pytest.raises(ValueError, match="not allowed"):
            r.circle(cx="25", cy="25", r="10")


class TestSvgBuilderBuildRender:
    """Build and render produce valid SVG output."""

    def test_build_and_render_basic(self):
        """Build + render produces SVG string."""
        builder = SvgBuilder()
        svg = builder.source.svg(width="200", height="200")
        svg.rect(x="10", y="10", width="80", height="80", fill="blue")

        builder.build()
        output = builder.render()

        assert "<svg" in output
        assert "<rect" in output
        assert 'fill="blue"' in output

    def test_self_closing_void_elements(self):
        """Void elements render as self-closing."""
        builder = SvgBuilder()
        svg = builder.source.svg(width="100", height="100")
        svg.circle(cx="50", cy="50", r="40")
        svg.line(x1="0", y1="0", x2="100", y2="100")

        builder.build()
        output = builder.render()

        assert "<circle" in output
        assert "/>" in output
        assert "</circle>" not in output

    def test_kebab_case_conversion(self):
        """Underscore attributes convert to kebab-case."""
        builder = SvgBuilder()
        svg = builder.source.svg(width="100", height="100")
        svg.rect(width="50", height="50", stroke_width="2", fill_opacity="0.5")

        builder.build()
        output = builder.render()

        assert 'stroke-width="2"' in output
        assert 'fill-opacity="0.5"' in output

    def test_text_with_content(self):
        """Text element renders with content."""
        builder = SvgBuilder()
        svg = builder.source.svg(width="200", height="100")
        svg.text("Hello SVG", x="10", y="50", font_size="24")

        builder.build()
        output = builder.render()

        assert ">Hello SVG</text>" in output
        assert 'font-size="24"' in output

    def test_nested_groups_render(self):
        """Nested groups render with indentation."""
        builder = SvgBuilder()
        svg = builder.source.svg(width="200", height="200")
        g = svg.g(id="layer1")
        g.rect(width="100", height="100", fill="red")

        builder.build()
        output = builder.render()

        assert '<g id="layer1">' in output
        assert "<rect" in output
        assert "</g>" in output

    def test_gradient_definition_render(self):
        """Gradient definitions render correctly."""
        builder = SvgBuilder()
        svg = builder.source.svg(width="100", height="100")
        defs = svg.defs()
        grad = defs.linearGradient(id="myGrad")
        grad.stop(offset="0%", stop_color="white")
        grad.stop(offset="100%", stop_color="black")

        builder.build()
        output = builder.render()

        assert '<linearGradient id="myGrad">' in output
        assert 'stop-color="white"' in output
        assert 'stop-color="black"' in output

    def test_complete_document(self):
        """Full SVG document renders correctly."""
        builder = SvgBuilder()
        svg = builder.source.svg(
            width="300", height="200", viewBox="0 0 300 200",
        )
        svg.title("Test Chart")
        svg.desc("A simple bar chart")

        g = svg.g(transform="translate(20,20)")
        g.rect(x="0", y="0", width="60", height="100", fill="steelblue")
        g.rect(x="80", y="30", width="60", height="70", fill="coral")
        g.rect(x="160", y="50", width="60", height="50", fill="gold")

        svg.text("Sales", x="150", y="190", text_anchor="middle")

        builder.build()
        output = builder.render()

        assert "<svg" in output
        assert ">Test Chart</title>" in output
        assert 'fill="steelblue"' in output
        assert 'text-anchor="middle"' in output
        assert ">Sales</text>" in output


class TestSvgBuilderReactivity:
    """SVG builder works with reactive data binding."""

    def test_pointer_in_attributes(self):
        """^pointer strings in attributes work after build+subscribe."""
        builder = SvgBuilder()
        builder.data["color"] = "red"

        svg = builder.source.svg(width="100", height="100")
        svg.circle(cx="50", cy="50", r="40", fill="^color")

        builder.build()
        builder.subscribe()

        output = builder.render()
        assert "<circle" in output
