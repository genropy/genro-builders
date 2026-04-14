# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""01 — Hello World: the simplest possible builder app.

What you learn:
    - HtmlManager: the standard entry point for HTML apps
    - main(source): populate the source Bag with elements
    - run(): setup + build in one call
    - page.render(): produce the HTML string

Prerequisites: None. This is the starting point.

Usage:
    python 01_hello_world.py
"""
from __future__ import annotations

from pathlib import Path

from genro_builders.contrib.html import HtmlManager


class HelloWorld(HtmlManager):
    """Minimal HTML app."""

    def main(self, source):
        body = source.body()
        body.h1("Hello World")
        body.p("This is my first builder page.")


app = HelloWorld()
app.run()

html = app.render()

output = Path(__file__).with_suffix(".html")
output.write_text(html)
print(html)
print(f"\nSaved to {output}")
