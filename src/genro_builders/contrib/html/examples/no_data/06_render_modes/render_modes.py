# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""06 — Render modes: one document, several outputs. See readme.md."""
from __future__ import annotations

from genro_builders.contrib.html import HtmlBuilder


class CustomPage(HtmlBuilder):
    def main(self, root):
        body = root.body()
        card = body.div(class_="card")
        card.h3("Title")
        card.p("Some text", color="#333")


if __name__ == "__main__":
    page = CustomPage()
    page.create()
    blocks = [
        ("html (default, compact)", page.render(target=False)),
        ("html (pretty)", page.render(target=False, pretty=True)),
        ("xml", page.render("xml", target=False, pretty=True)),
        ("yaml", page.render("yaml", target=False)),
    ]
    for label, out in blocks:
        print(f"=== {label} ===")
        print(out)
        print()
