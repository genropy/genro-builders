# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""00 — Hello world: the simplest possible page. See readme.md."""
from __future__ import annotations

from genro_builders.contrib.html import HtmlBuilder


class CustomPage(HtmlBuilder):
    def main(self, root):
        body = root.body()
        body.h1("Hello World")
        body.p("My first page with genro-builders.")


if __name__ == "__main__":
    page = CustomPage()
    page.set_render_target("output.html")
    page.create()
    page.render(pretty=True)
    print(page.rendered_target)
