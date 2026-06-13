# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""05 — Containers: blocks invoked from a node. See readme.md."""
from __future__ import annotations

from genro_builders import container
from genro_builders.contrib.html import HtmlBuilder


class CustomPage(HtmlBuilder):
    @container
    def card(self, pane, title, body, color="#3498db"):
        box = pane.div(class_="card", border_top=f"3px solid {color}")
        box.h3(title)
        box.p(body)

    @container
    def uiBadge(self, pane, text):
        pane.span(text, class_="badge")

    def main(self, root):
        body = root.body()
        body.card("Designer", "Alice", color="#e74c3c")
        body.card("Engineer", "Bob", color="#2ecc71")
        body.card("Manager", "Carol")
        body.uiBadge("from uiBadge")     # dispatch name = the method name
        body.uibadge("case insensitive")  # dispatch is case-insensitive


if __name__ == "__main__":
    page = CustomPage()
    page.set_render_target("output.html")
    page.create()
    page.render(pretty=True)
    print(page.rendered_target)
