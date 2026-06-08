# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""11 — Render modes: html, xml, yaml, pretty. See README.md."""
from __future__ import annotations

from pathlib import Path

from genro_builders.contrib.html import HtmlBuilder


class Page(HtmlBuilder):
    """One small document, rendered in several modes."""

    def main(self, root):
        body = root.body()
        card = body.div(class_="card")
        card.h3("Title")
        card.p("Some text", color="#333")


def _render(mode=None, *, pretty=False):
    page = Page()
    page.create()
    return page.render(mode=mode, pretty=pretty, target=False)


if __name__ == "__main__":
    blocks = [
        ("html (default, compact)", _render()),
        ("html (pretty)", _render(pretty=True)),
        ("xml", _render(mode="xml", pretty=True)),
        ("yaml", _render(mode="yaml")),
    ]
    parts = []
    for label, out in blocks:
        parts.append(f"=== {label} ===")
        parts.append(out)
        parts.append("")
    rendered = "\n".join(parts)

    output = Path(__file__).with_suffix(".txt")
    output.write_text(rendered)
    print(rendered)
    print(f"Saved to {output}")
