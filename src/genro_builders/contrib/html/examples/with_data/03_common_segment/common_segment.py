# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""03 — Common segment: data shared across builders via ``_:``. See readme.md."""
from __future__ import annotations

from genro_builders.builder import BuilderHandler
from genro_builders.contrib.html import HtmlBuilder


class SiteHandler(BuilderHandler):
    def setup(self, data):
        data.set_item("company", "Softwell S.r.l.")


class CustomPage(HtmlBuilder):
    def setup(self, data):
        data.set_item("title", "Welcome")

    def main(self, root):
        body = root.body()
        body.h1("^title")
        body.footer("^_:company")


if __name__ == "__main__":
    page = CustomPage()
    handler = SiteHandler()
    handler.add_builder(main=page)
    page.set_render_target("output.html")
    page.render(pretty=True)
    print(page.rendered_target)
