# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""01 — Introduction: a guided tour of CssBuilder (level 1).

What you learn:
    - Subclass `CssBuilder` and populate the source bag in
      `main(self, root)`.
    - Declare a `selector` at the top, attach a `rule` for the
      property block.
    - Use `selectorList` when multiple selectors share the same
      rule and variants.
    - Declare `@media` and `@supports` variants of the selector
      inline, with property kwargs applied to the parent.
    - Use CSS Nesting by attaching child selectors inside a
      selector.
    - Declare CSS custom properties with ``cssvar(name, value=...)``.
    - Attach comments via ``comment="..."`` on any element.

Usage:
    python 01_introduction.py
"""
from __future__ import annotations

from pathlib import Path

from genro_builders.contrib.css import CssBuilder


class HelloCss(CssBuilder):
    """A small showcase of every level-1 feature."""

    def main(self, root):
        sheet = root.stylesheet()

        # 1. :root with CSS custom properties (variables).
        rt = sheet.selector(raw=":root")
        rt.cssvar("primary-color", value="#3498db",
                  comment="Brand color, used for primary CTAs")
        rt.cssvar("spacing", value="8px")

        # 2. Single selector built from structured kwargs.
        btn = sheet.selector(tag="button", class_="primary")
        btn.rule(
            background_color="var(--primary-color)",
            color="white",
            padding="var(--spacing)",
        )

        # 3. Selector list — multiple selectors share one block.
        cards = sheet.selectorList()
        cards.selector(class_="card")
        cards.selector(class_="panel")
        cards.selector(class_="dialog")
        cards.rule(font_family="sans-serif")

        # 4. Media variant — extra rule with media kwarg.
        responsive = sheet.selector(class_="card2")
        responsive.rule(width="300px", padding="16px")
        responsive.rule(media="(max-width: 600px)",
                        width="100%", padding="8px")
        responsive.rule(media="print", color="black")

        # 5. Nesting (CSS Nesting moderno).
        card = sheet.selector(class_="card3")
        card.rule(padding="8px", background_color="#fafafa")
        title = card.selector(class_="title")
        title.rule(font_size="18px", font_weight="bold")
        hover = card.selector(raw="&:hover")
        hover.rule(background_color="#eef")

        # 6. Comment on a selector (short, inline).
        alert = sheet.selector(class_="alert", comment="warning state")
        alert.rule(color="red")

        # 7. Comment on a selector (long, block).
        dashboard = sheet.selector(
            class_="dashboard",
            comment=(
                "Grid layout for the dashboard summary cards; the "
                "auto-fit + minmax pattern lets cards reflow without "
                "media queries"
            ),
        )
        dashboard.rule(display="grid")


if __name__ == "__main__":
    page = HelloCss()
    page.create()
    rendered = page.render()

    output = Path("01_introduction.css")
    output.write_text(rendered)
    print(rendered)
    print(f"Saved to {output}")
