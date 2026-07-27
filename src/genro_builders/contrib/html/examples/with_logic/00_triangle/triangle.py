# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""00 — Triangle: a dataFormula computes the area at start. See readme.md."""
from __future__ import annotations

from genro_builders.builder import BuilderHandler
from genro_builders.contrib.html import HtmlBuilder


class CustomPage(HtmlBuilder):
    @staticmethod
    def triangle_area(base, height):
        return base * height / 2

    def setup(self, data):
        data.set_item("base", 10)
        data.set_item("height", 4)

    def main(self, root):
        body = root.body()
        body.dataFormula(
            destination="area", func="triangle_area",
            base="^base", height="^height",
        )
        body.div("^base")
        body.div("^height")
        body.div("^area")


if __name__ == "__main__":
    page = CustomPage()
    handler = BuilderHandler()
    handler.add_builder(page)
    page.set_render_target("output.html")
    page.render(pretty=True)
    print(page.rendered_target)
