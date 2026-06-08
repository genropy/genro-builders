# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""01 — Introduction: the simplest possible page with HtmlBuilder.

What you learn:
    - Subclass `HtmlBuilder` and write the page in `main(self, root)`.
    - Populate the `source` Bag inside `main(self, root)`.
    - The two-phase lifecycle: `create()` -> `render()`.

Prerequisites: None. This is the starting point.

Usage:
    python 01_introduction.py
"""
from __future__ import annotations

from pathlib import Path

from genro_builders.contrib.html import HtmlBuilder


class HelloPage(HtmlBuilder):
    """Minimal HTML page with a heading and a paragraph."""

    def main(self, root):
        body = root.body()
        body.h1("Hello World")
        body.p("My first page with genro-builders.")


if __name__ == "__main__":
    page = HelloPage()
    page.create()
    rendered = page.render(pretty=True)

    output = Path(__file__).with_suffix(".html")
    output.write_text(rendered)
    print(rendered)
    print(f"Saved to {output}")
