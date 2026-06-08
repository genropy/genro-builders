# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""03 — Sub-builders: switch dialect mid-document. See readme.md."""
from __future__ import annotations

from genro_builders.contrib.html import HtmlBuilder


class CustomPage(HtmlBuilder):
    def main(self, root):
        body = root.body()

        # HTML hosting SVG: from body.svg() on, the SVG grammar is active.
        body.h2("Two shapes inline")
        s = body.svg(width=200, height=80, viewBox="0 0 200 80")
        s.circle(cx=40, cy=40, r=30, fill="#e74c3c")
        s.rect(x=90, y=20, width=90, height=40, fill="#3498db")

        # SVG hosting HTML: svg.html(...) re-enters HTML. The framework
        # wraps the subtree in <foreignObject> at render time.
        body.h2("HTML overlay inside SVG")
        s2 = body.svg(width=360, height=120, viewBox="0 0 360 120")
        s2.rect(x=0, y=0, width=360, height=120, rx=12, fill="#2c3e50")
        overlay = s2.html(x=20, y=20, width=320, height=80)
        card = overlay.div(color="white", padding="8px")
        card.div("Mixed content", font_weight="700")
        card.p("HTML rendered inside an SVG.", font_size="13px")


if __name__ == "__main__":
    page = CustomPage()
    page.set_render_target("output.html")
    page.create()
    page.render(pretty=True)
    print(page.rendered_target)
