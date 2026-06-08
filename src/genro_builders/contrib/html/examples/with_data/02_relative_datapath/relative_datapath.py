# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""02 — Relative datapath: a container scopes its children. See readme.md."""
from __future__ import annotations

from genro_builders.builder import BuilderHandler
from genro_builders.contrib.html import HtmlBuilder


class CustomPage(HtmlBuilder):
    def setup(self, data):
        data.set_item("invoice.number", "INV-001")
        data.set_item("invoice.total", 1250)

    def main(self, root):
        body = root.body()
        section = body.div(datapath="invoice")
        section.h1("^.number")
        section.p("^.total")


if __name__ == "__main__":
    page = CustomPage()
    handler = BuilderHandler()
    handler.add_builder(main=page)
    page.set_render_target("output.html")
    page.create()
    page.render(pretty=True)
    print(page.rendered_target)
