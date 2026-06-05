# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""End-to-end tests for SvgBuilder + SvgBuilderHandler."""

from __future__ import annotations

import io

import pytest

from genro_builders.contrib.svg import SvgBuilder, SvgBuilderHandler


def _render(main_fn):
    """Helper: build a handler with the given main and return its render output."""

    class _Page(SvgBuilderHandler):
        def main(self, root):
            main_fn(root)

    page = _Page()
    page.create()
    return page, page.render()


def test_svg_render_default_mode_is_svg():
    assert SvgBuilder._default_render_mode == "svg"


def test_svg_render_simple_rect_inside_svg():
    def build(root):
        s = root.svg(viewBox="0 0 100 100")
        s.rect(x=0, y=0, width=100, height=100, fill="red")

    _, out = _render(build)
    assert out == (
        '<svg viewBox="0 0 100 100">'
        '<rect x="0" y="0" width="100" height="100" fill="red" />'
        "</svg>"
    )


def test_svg_render_void_tag_self_closes_with_space():
    """SVG self-close uses ``<rect />`` (space before slash, W3C XHTML
    Appendix C.3 recommendation followed by SVG tools)."""
    def build(root):
        s = root.svg()
        s.circle(cx=10, cy=10, r=5)

    _, out = _render(build)
    assert "<circle " in out and " />" in out
    # ensure no slash-without-space variant slipped in
    assert "/>" in out
    assert "<circle/>" not in out


def test_svg_render_kebab_attribute_conversion():
    """``stroke_width`` becomes ``stroke-width`` per the kebab map."""
    def build(root):
        s = root.svg()
        s.rect(x=0, y=0, width=10, height=10, stroke_width=2, fill_opacity=0.5)

    _, out = _render(build)
    assert 'stroke-width="2"' in out
    assert 'fill-opacity="0.5"' in out


def test_svg_render_non_kebab_attribute_unchanged():
    """Plain attributes (``x``, ``y``, ``viewBox``) keep their name."""
    _, out = _render(lambda root: root.svg(viewBox="0 0 10 10"))
    assert 'viewBox="0 0 10 10"' in out


def test_svg_render_class_keyword_collision():
    _, out = _render(lambda root: root.svg(class_="chart"))
    assert 'class="chart"' in out


def test_svg_render_text_value_escape():
    def build(root):
        s = root.svg()
        s.text("a < b & c > d")

    _, out = _render(build)
    assert "a &lt; b &amp; c &gt; d" in out


def test_svg_render_attribute_quote_escape():
    _, out = _render(lambda root: root.svg(title='he said "hi"'))
    assert 'title="he said &quot;hi&quot;"' in out


def test_svg_render_nested_groups():
    def build(root):
        s = root.svg()
        g = s.g(transform="translate(10,10)")
        g.rect(x=0, y=0, width=5, height=5)

    _, out = _render(build)
    assert out == (
        "<svg>"
        '<g transform="translate(10,10)">'
        '<rect x="0" y="0" width="5" height="5" /></g>'
        "</svg>"
    )


def test_svg_render_returns_string_when_target_is_none():
    _, out = _render(lambda root: root.svg())
    assert isinstance(out, str)


def test_svg_render_target_writes_to_writable():
    class _Page(SvgBuilderHandler):
        def main(self, root):
            root.svg()

    page = _Page()
    page.create()
    buf = io.StringIO()
    page.set_render_target("svg", buf, default=True)
    result = page.render()
    assert result is None
    assert buf.getvalue() == "<svg></svg>"


def test_svg_render_target_invalid_object_raises_type_error():
    class _Page(SvgBuilderHandler):
        def main(self, root):
            root.svg()

    page = _Page()
    page.create()
    page.set_render_target("svg", 42, default=True)
    with pytest.raises(TypeError):
        page.render()
