# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""08 — Root dispatch: the root bag speaks the full grammar. See readme.md."""
from __future__ import annotations

from genro_builders.contrib.html import HtmlBuilder


class CustomPage(HtmlBuilder):
    def main(self, root):
        # A sub-builder element opened DIRECTLY on the root bag: from
        # <svg> down the active grammar is the SVG dialect, exactly as
        # when the element is created on a node.
        svg = root.svg(viewBox="0 0 100 100", width=120, height=120)
        svg.rect(x=10, y=10, width=80, height=80, fill="#3498db")
        svg.circle(cx=50, cy=50, r=25, fill="#e74c3c")


if __name__ == "__main__":
    page = CustomPage()
    page.set_render_target("output.html")
    page.create()
    page.render(pretty=True)
    print(page.rendered_target)
