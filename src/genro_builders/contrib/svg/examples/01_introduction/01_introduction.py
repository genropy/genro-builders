# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""01 — Introduction: the simplest possible image with SvgBuilderHandler.

What you learn:
    - Subclass `SvgBuilderHandler` and bind the SVG dialect to the handler.
    - Populate the `source` Bag inside `main(self, root)`.
    - The three-phase lifecycle: `create()` -> `build()` -> `render()`.

Prerequisites: None. This is the SVG starting point.

Usage:
    python 01_introduction.py
"""
from __future__ import annotations

from pathlib import Path

from genro_builders.contrib.svg import SvgBuilderHandler


class HelloSvg(SvgBuilderHandler):
    """Minimal SVG image with a coloured square and a circle on top."""

    def main(self, root):
        svg = root.svg(viewBox="0 0 100 100", width=200, height=200)
        svg.rect(x=10, y=10, width=80, height=80, fill="#3498db")
        svg.circle(cx=50, cy=50, r=30, fill="#e74c3c")


if __name__ == "__main__":
    page = HelloSvg()
    page.create()
    rendered = page.render()

    output = Path(__file__).with_suffix(".svg")
    output.write_text(rendered)
    print(rendered)
    print(f"\nSaved to {output}")
