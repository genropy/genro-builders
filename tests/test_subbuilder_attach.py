# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for the @subbuilder attach mechanism (decision 2, P4).

Verifies that declaring ``svg`` as ``@subbuilder("svg")`` on
``HtmlBuilder`` makes ``root.svg()``:

1. produce a node with ``_builder = SvgBuilder`` on its slot;
2. switch the grammar so SVG-only elements (``rect``, ``g``, ...)
   are accepted by descendants of ``<svg>``;
3. continue to reject SVG-only elements at HTML scope.

Symmetric checks for ``SvgBuilder.foreignObject`` re-entering HTML.

Also covers the source: ``handler.create()`` populates the source
with the sub-builder dialect attached to the sub-tree, which the
render walker then dispatches via ``node._builder``.
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


def test_svg_schema_declares_html_as_subbuilder_with_wrap_tag():
    """SVG's user-facing entry into HTML is the ``html`` tag; the
    framework wraps the rendered HTML in ``<foreignObject>`` at render
    time so the source stays readable while the markup is correct."""
    info = SvgBuilder()._get_schema_info("html")
    assert info.get("is_subbuilder") is True
    assert info.get("subbuilder_name") == "html"
    assert info.get("wrap_tag") == "foreignObject"


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
# Symmetric: SvgBuilder -> HtmlBuilder via the ``html`` subbuilder
# (rendered inside ``<foreignObject>`` thanks to wrap_tag)
# ---------------------------------------------------------------------------


class _SvgWithForeignHtml(SvgBuilderHandler):
    def main(self, root):
        s = root.svg()
        h = s.html()
        h.div("hello")


def test_svg_html_node_has_html_builder():
    page = _SvgWithForeignHtml()
    page.create()
    svg_node = next(iter(page.source))
    h_node = next(iter(svg_node.value))
    assert h_node.node_tag == "html"
    assert isinstance(h_node._builder, HtmlBuilder)


def test_svg_html_div_validated_by_html_grammar():
    page = _SvgWithForeignHtml()
    page.create()
    svg_node = next(iter(page.source))
    h_node = next(iter(svg_node.value))
    div_node = next(iter(h_node.value))
    assert div_node.node_tag == "div"
    assert div_node.value == "hello"


# ---------------------------------------------------------------------------
# Create-side propagation through the source subtree
# ---------------------------------------------------------------------------


def test_create_propagates_subbuilder_through_subtree():
    """``page.create()`` populates the source with the sub-builder
    dialect attached to the sub-tree."""
    page = _HtmlWithSvg()
    page.create()
    body_node = next(iter(page.source))
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
    out = page.render()
    # HTML body wraps the SVG host tag and content.
    assert out.startswith("<body><svg>")
    assert out.endswith("</svg></body>")
    # SvgRenderer renders <rect/> with a space (SVG convention).
    assert '<rect x="10" y="20" />' in out


def test_render_svg_html_wraps_in_foreignobject_with_xmlns():
    """SVG host wraps the HTML subtree in <foreignObject> with the
    xhtml namespace. The bare ``html`` source tag is replaced by the
    wrap tag — it does not appear in the markup."""
    page = _SvgWithForeignHtml()
    page.create()
    out = page.render()
    assert out.startswith(
        '<svg><foreignObject xmlns="http://www.w3.org/1999/xhtml">',
    )
    assert "<div>hello</div>" in out
    assert out.endswith("</foreignObject></svg>")
    # The user-facing source tag ``html`` does not surface in the output.
    assert "<html>" not in out


def test_render_wrap_tag_carries_user_attributes_from_source():
    """``svg.html(x=10, y=20, ...)``: user attributes belong on the wrap
    tag (foreignObject), since the source ``html`` node is replaced by
    it at render time. Without this, foreignObject would be unpositioned
    inside the SVG canvas."""

    class _Page(SvgBuilderHandler):
        def main(self, root):
            root.svg().html(x=10, y=20, width=200, height=100).div("ok")

    page = _Page()
    page.create()
    out = page.render()
    assert 'x="10"' in out
    assert 'y="20"' in out
    assert 'width="200"' in out
    assert 'height="100"' in out


def test_subbuilder_without_wrap_tag_renders_host_tag_verbatim():
    """When ``wrap_tag`` is not declared on the host subbuilder schema
    entry (the HTML→SVG case), the bare host tag (``<svg>``) is emitted
    verbatim around the sub-renderer output. No envelope inserted."""
    page = _HtmlWithSvg()
    page.create()
    out = page.render()
    # No xmlns inserted: the host tag is HTML5's native <svg>.
    assert "xmlns" not in out
    assert "<body><svg><rect" in out


def test_render_alternates_dialects_across_three_switches():
    """HTML -> SVG -> HTML -> resumes HTML at each boundary, using the
    user-facing ``svg.html()`` re-entry (wrap-tag mechanism)."""

    class _Mixed(HtmlBuilderHandler):
        def main(self, root):
            body = root.body()
            s = body.svg()
            s.rect(x=1, y=2)
            h = s.html()
            h.div("inside-svg")
            body.p("back-to-html")

    page = _Mixed()
    page.create()
    out = page.render()
    # Outer HTML body wraps everything.
    assert out.startswith("<body><svg>")
    # Rect in SVG style.
    assert '<rect x="1" y="2" />' in out
    # Re-entry to HTML wraps as <foreignObject xmlns="..."> automatically.
    assert (
        '<foreignObject xmlns="http://www.w3.org/1999/xhtml">'
        "<div>inside-svg</div>"
        "</foreignObject>"
    ) in out
    # Sibling after </svg> resumes HTML.
    assert "</svg><p>back-to-html</p></body>" in out
