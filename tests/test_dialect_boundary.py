# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Dialect boundaries in the render walk.

Every per-node phase runs on the renderer of the node's own dialect;
the boundary envelope (the ``subbuilder`` node) keeps its attributes
literal. Covered crossings:

- HTML -> SVG (``body.svg(...)``): geometry attrs survive on the
  envelope and on the shapes; no HTML CSS-kwarg magic leaks into SVG.
- SVG -> HTML (``svg.html(...)``): the envelope renders as a sized
  ``<foreignObject>`` with the XHTML namespace; inside it the HTML
  rules apply again (CSS kwargs compose ``style``).
"""
from __future__ import annotations

from genro_builders.contrib.html import HtmlBuilder


def _render(main_fn):
    class Page(HtmlBuilder):
        def main(self, root) -> None:
            main_fn(root)

    page = Page()
    page.create()
    return page.render(target=False)


def test_svg_inside_html_keeps_geometry_attributes():
    def main(root):
        svg = root.body().svg(width=120, height=60)
        svg.rect(x=4, y=4, width=20, height=20, fill="tomato", stroke_width=2)

    out = _render(main)
    assert '<svg width="120" height="60">' in out
    assert (
        '<rect x="4" y="4" width="20" height="20" fill="tomato"'
        ' stroke-width="2" />' in out
    )
    assert "style=" not in out


def test_html_inside_svg_renders_a_sized_foreignobject():
    def main(root):
        svg = root.body().svg(width=200, height=100)
        fo = svg.html(x=10, y=10, width=180, height=80)
        fo.div("hello", color="red")

    out = _render(main)
    assert (
        '<foreignObject x="10" y="10" width="180" height="80"'
        ' xmlns="http://www.w3.org/1999/xhtml">' in out
    )
    # Inside the boundary the HTML rules apply again: CSS kwargs
    # compose the style attribute.
    assert '<div style="color: red">hello</div>' in out


def test_nested_round_trip_each_dialect_governs_its_own_nodes():
    def main(root):
        svg = root.body().svg(width=50)
        inner = svg.html(width=40)
        inner.span("x", font_weight="bold")

    out = _render(main)
    assert '<svg width="50">' in out                      # envelope: literal
    assert '<foreignObject width="40"' in out             # envelope: literal
    assert '<span style="font-weight: bold">x</span>' in out   # HTML rules inside
