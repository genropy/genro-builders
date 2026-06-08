# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""01 — Inline styling: CSS as kwargs and Genro macros. See readme.md."""
from __future__ import annotations

from genro_builders.contrib.html import HtmlBuilder


class CustomPage(HtmlBuilder):
    def main(self, root):
        body = root.body()

        # Plain CSS kwargs.
        body.div(
            "CSS as kwargs",
            color="white", background="#3498db", padding="12px",
        )

        # Sub-property kwargs.
        body.div(
            "Sub-property kwargs",
            color="white", background="#2c3e50",
            padding_top=12, padding_bottom=12, padding_left=24,
            font_size="14px", text_align="center",
        )

        # Explicit style merged with kwargs (kwargs win on collision).
        body.div(
            "Explicit style + kwargs",
            style="color: blue; padding: 6px",
            color="white", background="#e67e22",
        )

        # style_ escape for properties outside the curated list.
        body.div(
            "style_ escape: aspect-ratio",
            background="#16a085", color="white",
            style_aspect_ratio="3 / 1",
        )

        # Genro macro: rounded.
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

        # Genro macro: transform.
        body.div(
            "transform macro: rotate + scale",
            background="#f1c40f", color="#2c3e50", padding="12px",
            transform_rotate=-3, transform_scale=0.95,
            display="inline-block",
        )

        # Genro macro: filter.
        body.div(
            "filter macro: blur + contrast",
            background="#e74c3c", color="white", padding="12px",
            filter_blur=2, filter_contrast=80,
        )


if __name__ == "__main__":
    page = CustomPage()
    page.set_render_target("output.html")
    page.create()
    page.render(pretty=True)
    print(page.rendered_target)
