# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""04 — Reactive formula: change an input, the data_formula recomputes.

A data_formula computes the triangle area from ^base and ^height. Inside a
live section an input is changed; the formula recomputes the area and the
div that reads ^area re-renders. A chained formula (^area -> dbl) shows the
cascade: base -> area -> dbl all propagate in one live section.
"""
from __future__ import annotations

from genro_builders.contrib.html import HtmlBuilder
from genro_builders.contrib.html.examples.reactive.example_app import ExampleApp


class CustomPage(HtmlBuilder):
    @staticmethod
    def triangle_area(base, height):
        return base * height / 2

    @staticmethod
    def double(area):
        return area * 2

    def setup(self, data):
        data.set_item("base", 10)
        data.set_item("height", 4)

    def main(self, root):
        body = root.body()
        body.data_formula(
            destination="area", func="triangle_area",
            base="^base", height="^height", _on_start=True,
        )
        body.data_formula(
            destination="dbl", func="double", area="^area", _on_start=True,
        )
        body.div("^area")
        body.div("^dbl")


class CustomApp(ExampleApp):
    def change_00_base(self, source, data):
        data.set_item("main.base", 20)          # area 20->40, dbl 40->80

    def change_01_height(self, source, data):
        data.set_item("main.height", 5)         # area 40->50, dbl 80->100


if __name__ == "__main__":
    app = CustomApp((CustomPage(), "output.html"))
    print(app.page.rendered_target)
    app.run()
