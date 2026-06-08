# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""04 — Methods: factor repeated structure into page methods. See readme.md."""
from __future__ import annotations

from genro_builders.contrib.html import HtmlBuilder


class CustomPage(HtmlBuilder):
    def card(self, parent, title, body, color="#3498db"):
        box = parent.div(class_="card", border_top=f"3px solid {color}")
        box.h3(title)
        box.p(body)
        return box

    def main(self, root):
        body = root.body()
        self.card(body, "Designer", "Alice", color="#e74c3c")
        self.card(body, "Engineer", "Bob", color="#2ecc71")
        self.card(body, "Manager", "Carol")


if __name__ == "__main__":
    page = CustomPage()
    page.set_render_target("output.html")
    page.create()
    page.render(pretty=True)
    print(page.rendered_target)
