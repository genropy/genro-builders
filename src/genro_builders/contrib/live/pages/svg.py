# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""SVG demo: vector graphics built inside an HTML page.

Shows the HTML builder reaching into SVG: ``body.svg(...)`` opens an
``<svg>`` subtree whose children (``circle``, ``rect``, ``text``, ...) are
resolved against the SVG grammar. A couple of attributes are bound to data
(``^.label``, ``^.fill``) so the shape can be re-styled from the REPL.
"""

from __future__ import annotations

from ..interactive_demo import InteractiveDemo

DEMO_TITLE = "SVG shapes"


class Demo(InteractiveDemo):
    """A small scene: a circle, a rectangle and a label.

    Data lives under ``shape``: ``shape.label``, ``shape.fill``.
    """

    def setup(self):
        self.set_data("shape.label", "SVG")
        self.set_data("shape.fill", "#2c5f8a")

    def main(self, root):
        body = root.body(datapath="shape")
        body.link(rel="stylesheet", href="demo_css")
        body.h1("Vector graphics")
        svg = body.svg(viewBox="0 0 200 120", width=200, height=120)
        svg.circle(cx=60, cy=60, r=45, fill="^.fill")
        svg.rect(x=120, y=25, width=60, height=60, rx=8, fill="orange")
        svg.text("^.label", x=42, y=66, fill="white", font_size=20)


if __name__ == "__main__":
    demo = Demo()
    demo.create()
    print(demo.render())
