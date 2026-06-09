# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""00 — Hello data: the message text comes from the data. See readme.md."""
from __future__ import annotations

from genro_builders.builder import BuilderHandler
from genro_builders.contrib.html import HtmlBuilder


class CustomPage(HtmlBuilder):
    def setup(self, data):
        data.set_item("message", "Hello Folk")

    def main(self, root):
        root.body().h1("^message")


if __name__ == "__main__":
    page = CustomPage()
    handler = BuilderHandler()
    handler.add_builder(main=page)
    page.set_render_target("output.html")
    page.render(pretty=True)
    print(page.rendered_target)
