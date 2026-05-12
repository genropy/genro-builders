# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""01 — Hello World: the simplest possible page with HtmlBuilderHandler.

What you learn:
    - Subclass `HtmlBuilderHandler` and bind a dialect to the handler.
    - Populate the `source` Bag inside `main(self, root)`.
    - The three-phase lifecycle: `create()` -> `build()` -> `render()`.

Prerequisites: None. This is the starting point.

Usage:
    python 01_hello_world.py
"""
from __future__ import annotations

from pathlib import Path

from genro_builders.contrib.html import HtmlBuilderHandler


class HelloPage(HtmlBuilderHandler):
    """Minimal HTML page with a heading and a paragraph."""

    def main(self, root):
        body = root.body()
        body.h1("Hello World")
        body.p("My first page with genro-builders.")


if __name__ == "__main__":
    page = HelloPage()
    page.create()
    page.build()
    rendered = page.render()

    output = Path(__file__).with_suffix(".html")
    output.write_text(rendered)
    print(rendered)
    print(f"\nSaved to {output}")
