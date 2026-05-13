# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for the @subbuilder attach mechanism (decision 2, P4).

Verifies that declaring ``svg`` as ``@subbuilder("svg")`` on
``HtmlBuilder`` makes ``root.svg()``:

1. produce a node with ``_builder = SvgBuilder`` on its slot;
2. switch the grammar so SVG-only elements (``rect``, ``g``, ...)
   are accepted by descendants of ``<svg>``;
3. continue to reject SVG-only elements at HTML scope.

Symmetric checks for ``SvgBuilder.foreignObject`` re-entering HTML.

Also covers the build phase: ``handler.build()`` mirrors the
sub-tree into ``built`` preserving the sub-builder dialect.
"""
from __future__ import annotations

import pytest

from genro_builders.contrib.html import HtmlBuilder, HtmlBuilderHandler
from genro_builders.contrib.svg import SvgBuilder, SvgBuilderHandler


# ---------------------------------------------------------------------------
# Schema declaration
# ---------------------------------------------------------------------------


def test_html_schema_declares_svg_as_subbuilder():
    info = HtmlBuilder()._get_schema_info("svg")
    assert info.get("is_subbuilder") is True
    assert info.get("subbuilder_name") == "svg"


def test_svg_schema_declares_foreignobject_as_subbuilder():
    info = SvgBuilder()._get_schema_info("foreignObject")
    assert info.get("is_subbuilder") is True
    assert info.get("subbuilder_name") == "html"


# ---------------------------------------------------------------------------
# Source-side attach: HtmlBuilder -> SvgBuilder via <svg>
# ---------------------------------------------------------------------------


class _HtmlWithSvg(HtmlBuilderHandler):
    def main(self, root):
        body = root.body()
        s = body.svg()
        s.rect(x=10, y=20)


def test_html_svg_node_has_svg_builder():
    """``<svg>`` carries an instance of ``SvgBuilder`` on its slot."""
    page = _HtmlWithSvg()
    page.create()
    body_node = next(iter(page.source))
    svg_node = next(iter(body_node.value))
    assert isinstance(svg_node._builder, SvgBuilder)


def test_html_svg_rect_validated_by_svg_grammar():
    """``rect`` is created (valid under <svg> per SVG grammar)."""
    page = _HtmlWithSvg()
    page.create()
    body_node = next(iter(page.source))
    svg_node = next(iter(body_node.value))
    rect_node = next(iter(svg_node.value))
    assert rect_node.node_tag == "rect"
    assert rect_node.attr.get("x") == 10


def test_html_svg_does_not_leak_html_grammar():
    """``<svg>.div()`` must fail: div is not in SVG grammar."""

    class _Bad(HtmlBuilderHandler):
        def main(self, root):
            body = root.body()
            body.svg().div()

    with pytest.raises(AttributeError):
        _Bad().create()


def test_html_rect_at_root_still_fails():
    """``body.rect()`` continues to fail: rect is not in HTML grammar."""

    class _Bad(HtmlBuilderHandler):
        def main(self, root):
            body = root.body()
            body.rect(x=10)

    with pytest.raises(AttributeError):
        _Bad().create()


# ---------------------------------------------------------------------------
# Symmetric: SvgBuilder -> HtmlBuilder via <foreignObject>
# ---------------------------------------------------------------------------


class _SvgWithForeignHtml(SvgBuilderHandler):
    def main(self, root):
        s = root.svg()
        fo = s.foreignObject()
        fo.div("hello")


def test_svg_foreignobject_node_has_html_builder():
    page = _SvgWithForeignHtml()
    page.create()
    svg_node = next(iter(page.source))
    fo_node = next(iter(svg_node.value))
    assert isinstance(fo_node._builder, HtmlBuilder)


def test_svg_foreignobject_div_validated_by_html_grammar():
    page = _SvgWithForeignHtml()
    page.create()
    svg_node = next(iter(page.source))
    fo_node = next(iter(svg_node.value))
    div_node = next(iter(fo_node.value))
    assert div_node.node_tag == "div"
    assert div_node.value == "hello"


# ---------------------------------------------------------------------------
# Build: sub-builder subtree mirrors into built
# ---------------------------------------------------------------------------


def test_build_propagates_subbuilder_through_subtree():
    """``page.build()`` produces built with sub-tree intact."""
    page = _HtmlWithSvg()
    page.create()
    page.build()
    body_node = next(iter(page.built))
    svg_node = next(iter(body_node.value))
    rect_node = next(iter(svg_node.value))
    assert svg_node.node_tag == "svg"
    assert rect_node.node_tag == "rect"
    assert rect_node.attr.get("x") == 10
    assert isinstance(svg_node._builder, SvgBuilder)


# ---------------------------------------------------------------------------
# Render polymorphism (P5)
# ---------------------------------------------------------------------------


def test_render_html_with_svg_uses_svg_dialect():
    """Host (HTML) delegates the SVG subtree to ``SvgRenderer``; the
    output mixes HTML void-tag style with SVG's space-before-slash."""
    page = _HtmlWithSvg()
    page.create()
    page.build()
    out = page.render()
    # HTML body wraps the SVG host tag and content.
    assert out.startswith("<body><svg>")
    assert out.endswith("</svg></body>")
    # SvgRenderer renders <rect/> with a space (SVG convention).
    assert '<rect x="10" y="20" />' in out


def test_render_svg_with_foreignobject_uses_html_dialect():
    """SVG host delegates foreignObject subtree to ``HtmlRenderer``."""
    page = _SvgWithForeignHtml()
    page.create()
    page.build()
    out = page.render()
    assert out.startswith("<svg><foreignObject>")
    assert "<div>hello</div>" in out
    assert out.endswith("</foreignObject></svg>")


def test_render_alternates_dialects_across_three_switches():
    """HTML -> SVG -> HTML -> HTML resumes at each boundary."""

    class _Mixed(HtmlBuilderHandler):
        def main(self, root):
            body = root.body()
            s = body.svg()
            s.rect(x=1, y=2)
            fo = s.foreignObject()
            fo.div("inside-svg")
            body.p("back-to-html")

    page = _Mixed()
    page.create()
    page.build()
    out = page.render()
    # Outer HTML body wraps everything.
    assert out.startswith("<body><svg>")
    # Rect in SVG style.
    assert '<rect x="1" y="2" />' in out
    # Re-entry to HTML inside foreignObject keeps HTML void-tag style.
    assert "<foreignObject><div>inside-svg</div></foreignObject>" in out
    # Sibling after </svg> resumes HTML.
    assert "</svg><p>back-to-html</p></body>" in out
