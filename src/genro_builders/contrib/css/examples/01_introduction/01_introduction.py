# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""01 — Introduction: a guided tour of CssBuilder (level 1).

What you learn:
    - Subclass `CssBuilderHandler` and populate the source bag in
      `main(self, root)`.
    - Build rules with property kwargs (kebab-case via underscores).
    - Declare selectors as children of a rule, one ``selector`` call
      per selector-list entry; multiple selectors become a comma list.
    - Use structured kwargs (``tag``, ``id``, ``_class``, ``classes``,
      ``attr``) for compound selectors, ``raw`` for combinators and
      anything not covered.
    - Declare CSS custom properties with ``cssvar(name, value=...)``.
    - Attach comments via ``comment="..."`` on any element (short
      inline, long block).

Usage:
    python 01_introduction.py
"""
from __future__ import annotations

from pathlib import Path

from genro_builders.contrib.css import CssBuilderHandler


class HelloCss(CssBuilderHandler):
    """A small showcase of every level-1 feature."""

    def main(self, root):
        sheet = root.stylesheet()

        # 1. :root with CSS custom properties (variables).
        rt = sheet.rule()
        rt.selector(raw=":root")
        rt.cssvar("primary-color", value="#3498db",
                  comment="Brand color, used for primary CTAs")
        rt.cssvar("spacing", value="8px")

        # 2. A compound selector built from structured kwargs.
        r2 = sheet.rule(
            background_color="var(--primary-color)",
            color="white",
            padding="var(--spacing)",
        )
        r2.selector(tag="button", _class="primary")

        # 3. Multiple selectors share one declaration block.
        r3 = sheet.rule(font_family="sans-serif")
        r3.selector(_class="card")
        r3.selector(_class="panel")
        r3.selector(_class="dialog")

        # 4. A selector with combinator and pseudo-class via raw.
        r4 = sheet.rule(opacity="0.6")
        r4.selector(_class="card", raw="> .icon:hover")

        # 5. A rule with a short inline comment.
        r5 = sheet.rule(color="red", comment="warning state")
        r5.selector(_class="alert")

        # 6. A rule with a long block comment.
        r6 = sheet.rule(
            display="grid",
            comment=(
                "Grid layout for the dashboard summary cards; the "
                "auto-fit + minmax pattern lets cards reflow without "
                "media queries"
            ),
        )
        r6.selector(_class="dashboard")


if __name__ == "__main__":
    page = HelloCss()
    page.create()
    page.build()
    rendered = page.render()

    output = Path(__file__).with_suffix(".css")
    output.write_text(rendered)
    print(rendered)
    print(f"Saved to {output}")
