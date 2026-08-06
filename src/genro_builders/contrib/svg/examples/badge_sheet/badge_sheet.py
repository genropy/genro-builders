# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Badge sheet — demo di @container.

What you learn:
    - Decorate a builder method with @container to expose it as a
      block invocable from any node in the source bag.
    - The first arg after self (convention: ``pane``) is the node from
      which the block was invoked.
    - Dispatch is case-insensitive (``svg.Badge`` and ``svg.badge``
      invoke the same block).
    - The block can return a node to allow chaining.

Usage:
    python badge_sheet.py
"""
from __future__ import annotations

from pathlib import Path

from genro_builders import container
from genro_builders.contrib.svg import SvgBuilder


class BadgeSheet(SvgBuilder):
    """Sheet of three name badges arranged in a grid."""

    @container
    def badge(self, pane, title, subtitle, color="#3498db", x=0, y=0):
        g = pane.g(transform=f"translate({x},{y})")
        g.rect(x=0, y=0, width=200, height=80, fill=color, rx=10)
        g.text(title, x=20, y=30, font_size=18, fill="white")
        g.text(subtitle, x=20, y=55, font_size=14, fill="white")
        return g

    def main(self, root):
        svg = root.svg(viewBox="0 0 440 200", width=440, height=200)
        svg.badge(title="Alice", subtitle="Designer", color="#e74c3c", x=10, y=10)
        svg.Badge(title="Bob", subtitle="Engineer", color="#2ecc71", x=230, y=10)
        svg.badge(title="Carol", subtitle="Manager", color="#3498db", x=10, y=110)


if __name__ == "__main__":
    page = BadgeSheet()
    page.create()
    rendered = page.render()

    output = Path("badge_sheet.svg")
    output.write_text(rendered)
    print(rendered)
    print(f"\nSaved to {output}")
