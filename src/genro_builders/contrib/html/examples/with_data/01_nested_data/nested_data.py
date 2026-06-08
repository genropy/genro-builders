# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""01 — Nested data: pointers into a dotted data path. See readme.md."""
from __future__ import annotations

from genro_builders.builder import BuilderHandler
from genro_builders.contrib.html import HtmlBuilder


class CustomPage(HtmlBuilder):
    def setup(self, data):
        data.set_item("user.name", "Ada Lovelace")
        data.set_item("user.email", "ada@example.com")

    def main(self, root):
        body = root.body()
        body.h1("^user.name")
        body.p("^user.email")


if __name__ == "__main__":
    page = CustomPage()
    handler = BuilderHandler()
    handler.add_builder(main=page)
    page.set_render_target("output.html")
    page.create()
    page.render(pretty=True)
    print(page.rendered_target)
