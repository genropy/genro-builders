# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""03 — Root logic: data-elements attached on the root bag. See readme.md."""
from __future__ import annotations

from genro_builders.builder import BuilderHandler
from genro_builders.contrib.html import HtmlBuilder


class CustomPage(HtmlBuilder):
    @staticmethod
    def gross(price, tax):
        return round(price * (1 + tax), 2)

    def main(self, root):
        # Data-elements created DIRECTLY on the root bag: the positional
        # fields map onto the schema names (destination, value) exactly
        # as when the element is created on a node.
        root.data_setter("price", 100)
        root.data_setter("tax", 0.22)
        root.data_formula(
            destination="total", func="gross",
            price="^price", tax="^tax", _on_start=True,
        )
        body = root.body()
        body.div("^price")
        body.div("^tax")
        body.div("^total")


if __name__ == "__main__":
    page = CustomPage()
    handler = BuilderHandler()
    handler.add_builder(page)
    page.set_render_target("output.html")
    page.render(pretty=True)
    print(page.rendered_target)
