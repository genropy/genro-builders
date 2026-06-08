# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""02 — Inline styling: CSS as kwargs and Genro macros.

What you learn:
    - Pass CSS properties as keyword arguments (``color="red"``).
    - Use sub-property kwargs (``padding_top=10``).
    - Merge with explicit ``style="..."`` (kwargs win on collision).
    - Escape prefix ``style_<prop>`` for properties outside the curated list.
    - Genro macros: ``rounded``, ``transform``, ``filter`` with
      ``<macro>_<sub>`` single-underscore sub-kwargs.

Prerequisites: 01_introduction.

Usage:
    python 02_inline_styling.py
"""
from __future__ import annotations

from pathlib import Path

from genro_builders.contrib.html import HtmlBuilder


class StylingShowcase(HtmlBuilder):
    """A single page that demonstrates each inline-styling form."""

    def main(self, root):
        body = root.body()

        # 1. Plain CSS kwargs
        body.div(
            "CSS as kwargs",
            color="white", background="#3498db", padding="12px",
        )

        # 2. Sub-property kwargs
        body.div(
            "Sub-property kwargs",
            color="white", background="#2c3e50",
            padding_top=12, padding_bottom=12, padding_left=24,
            font_size="14px", text_align="center",
        )

        # 3. Explicit style merged with kwargs
        body.div(
            "Explicit style + kwargs",
            style="color: blue; padding: 6px",
            color="white", background="#e67e22",
        )

        # 4. style_ escape for properties outside the curated list
        body.div(
            "style_ escape: aspect-ratio",
            background="#16a085", color="white",
            style_aspect_ratio="3 / 1",
        )

        # 5. Genro macro: rounded
        body.div(
            "rounded macro (all corners)",
            background="#9b59b6", color="white", padding="12px",
            rounded=12,
        )
        body.div(
            "rounded macro (top corners only)",
            background="#8e44ad", color="white", padding="12px",
            rounded_top=20,
        )

        # 6. Genro macro: transform
        body.div(
            "transform macro: rotate + scale",
            background="#f1c40f", color="#2c3e50", padding="12px",
            transform_rotate=-3, transform_scale=0.95,
            display="inline-block",
        )

        # 7. Genro macro: filter
        body.div(
            "filter macro: blur + contrast",
            background="#e74c3c", color="white", padding="12px",
            filter_blur=2, filter_contrast=80,
        )


if __name__ == "__main__":
    page = StylingShowcase()
    page.create()
    rendered = page.render(pretty=True)

    output = Path(__file__).with_suffix(".html")
    output.write_text(rendered)
    print(rendered)
    print(f"Saved to {output}")
