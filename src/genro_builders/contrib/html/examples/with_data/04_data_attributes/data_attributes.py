# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""04 — Data attributes: a datum carries a value AND attributes. See readme.md."""
from __future__ import annotations

from genro_builders.builder import BuilderHandler
from genro_builders.contrib.html import HtmlBuilder


class CustomPage(HtmlBuilder):
    def setup(self, data):
        # A datum is not only a value: it can carry attributes too.
        data.set_item("name", "John", color="red", background="yellow")

    def main(self, root):
        # The value is read with ^name; an attribute of the datum with ^name?attr.
        root.body().div(
            "^name", color="^name?color", background="^name?background",
        )


if __name__ == "__main__":
    page = CustomPage()
    handler = BuilderHandler()
    handler.add_builder(page)
    page.set_render_target("output.html")
    page.render(pretty=True)
    print(page.rendered_target)
