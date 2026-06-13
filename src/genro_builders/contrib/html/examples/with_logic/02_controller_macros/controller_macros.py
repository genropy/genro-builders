# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""02 — Controller macros: dataSetter + dataController with SET/GET/PUT/FIRE.

See readme.md.
"""
from __future__ import annotations

from genro_builders.builder import BuilderHandler
from genro_builders.contrib.html import HtmlBuilder


class CustomPage(HtmlBuilder):
    @staticmethod
    def init_box(node, start):
        node.SET(".count", start)                      # write (origin)
        node.PUT(".quiet", node.GET(".count") + 1)     # quiet write + read
        node.FIRE(".ping")                             # event, not stored

    def main(self, root):
        body = root.body()
        box = body.div(datapath="box")
        box.dataSetter(".start", 7)
        box.dataController(func="init_box", start="^.start", _on_start=True)
        box.span("^.start")
        box.span("^.count")
        box.span("^.quiet")
        box.span("^.ping")


if __name__ == "__main__":
    page = CustomPage()
    handler = BuilderHandler()
    handler.add_builder(page)
    page.set_render_target("output.html")
    page.render(pretty=True)
    print(page.rendered_target)
