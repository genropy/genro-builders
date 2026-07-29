# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""05 — SVG pointer: a data pointer read inside a nested SVG sub-builder.

The page is HTML; ``body.svg(...)`` opens an SVG sub-builder. A shape in
that subtree binds an attribute to data (``fill="^fill"``). This exercises
the case where a pointer is resolved by a *sub-builder*, not the page
builder — the sub-builder must still reach the document's datastore to
read the datum (``get_subbuilder`` propagates ``builder.data``).
"""
from __future__ import annotations

from genro_builders.contrib.html import HtmlBuilder


class CustomPage(HtmlBuilder):
    def setup(self, data):
        data.set_item("fill", "#3498db")
        data.set_item("label", "SVG")

    def main(self, root):
        body = root.body()
        svg = body.svg(viewBox="0 0 200 120", width=200, height=120)
        svg.circle(cx=60, cy=60, r=45, fill="^fill")
        svg.text("^label", x=42, y=66, fill="white", font_size=20)


if __name__ == "__main__":
    page = CustomPage()
    page.create()
    page.set_render_target("output.html")
    page.render(pretty=True)
    print(page.rendered_target)
