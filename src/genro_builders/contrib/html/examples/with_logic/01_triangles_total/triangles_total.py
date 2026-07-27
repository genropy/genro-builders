# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""01 — Triangles + total: a loop of formulas and a sum. See readme.md."""
from __future__ import annotations

from genro_builders.contrib.html import HtmlBuilder


class CustomPage(HtmlBuilder):
    @staticmethod
    def triangle_area(base, height):
        return base * height / 2

    @staticmethod
    def sum_areas(**areas):
        return sum(v for v in areas.values() if v is not None)

    def main(self, root):
        body = root.body()
        triangoli = body.div(datapath="triangoli")
        for i in range(1, 6):
            row = triangoli.div(datapath=f".tr{i}")
            row.dataSetter(".base", i * 2)
            row.dataSetter(".height", i)
            row.dataFormula(
                destination=".area", func="triangle_area",
                base="^.base", height="^.height",
            )
            row.span("^.base")
            row.span("^.height")
            row.span("^.area")
        body.dataFormula(
            destination="total", func="sum_areas",
            a1="^triangoli.tr1.area", a2="^triangoli.tr2.area",
            a3="^triangoli.tr3.area", a4="^triangoli.tr4.area",
            a5="^triangoli.tr5.area",
        )
        body.div("^total")


if __name__ == "__main__":
    page = CustomPage()
    page.create()
    page.set_render_target("output.html")
    page.render(pretty=True)
    print(page.rendered_target)
