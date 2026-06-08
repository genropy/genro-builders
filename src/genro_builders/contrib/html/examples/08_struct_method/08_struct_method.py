# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""08 — Struct methods: reusable blocks. See README.md for the walkthrough."""
from __future__ import annotations

from pathlib import Path

from genro_builders import struct_method
from genro_builders.contrib.html import HtmlBuilder


class Section1(HtmlBuilder):
    """A reusable card block invoked several times from any node."""

    @struct_method
    def card(self, pane, title, body, color="#3498db"):
        box = pane.div(class_="card", border_top=f"3px solid {color}")
        box.h3(title)
        box.p(body)

    def main(self, root):
        body = root.body()
        body.card("Designer", "Alice", color="#e74c3c")
        body.card("Engineer", "Bob", color="#2ecc71")
        body.card("Manager", "Carol")


class Section2(HtmlBuilder):
    """Case-insensitive dispatch and prefix-stripped explicit names."""

    @struct_method
    def ui_badge(self, pane, text):
        pane.span(text, class_="badge")

    def main(self, root):
        body = root.body()
        body.badge("from ui_badge")   # prefix 'ui_' stripped -> 'badge'
        body.Badge("case insensitive")  # 'Badge' dispatches the same


def _render_section(builder_cls, *, pretty=True):
    page = builder_cls()
    page.create()
    return page.render(pretty=pretty)


if __name__ == "__main__":
    sections = [Section1, Section2]
    parts = []
    for i, cls in enumerate(sections, 1):
        parts.append(f"<!-- Section {i} -->")
        parts.append(_render_section(cls))
        parts.append("")
    rendered = "\n".join(parts)

    output = Path(__file__).with_suffix(".html")
    output.write_text(rendered)
    print(rendered)
    print(f"Saved to {output}")
