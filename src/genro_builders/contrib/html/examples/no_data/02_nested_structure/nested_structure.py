# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""02 — Nested structure: deep trees from local variables. See readme.md."""
from __future__ import annotations

from genro_builders.contrib.html import HtmlBuilder


class CustomPage(HtmlBuilder):
    def main(self, root):
        body = root.body()

        header = body.header(background="#2c3e50", color="white", padding="16px")
        header.h1("Dashboard")
        nav = header.nav()
        nav.a("Home", href="#")
        nav.a("Reports", href="#")

        content = body.main(padding="16px")
        section = content.section()
        section.h2("Cards")
        grid = section.div(display="grid", gap="12px")
        for title, text in (
            ("Sales", "Up 12% this quarter."),
            ("Users", "1,204 active."),
            ("Errors", "None reported."),
        ):
            card = grid.div(border="1px solid #ddd", border_radius=8, padding="12px")
            card.h3(title)
            card.p(text)

        footer = body.footer(padding="16px", color="#7f8c8d")
        footer.p("© 2025 Example")


if __name__ == "__main__":
    page = CustomPage()
    page.set_render_target("output.html")
    page.create()
    page.render(pretty=True)
    print(page.rendered_target)
