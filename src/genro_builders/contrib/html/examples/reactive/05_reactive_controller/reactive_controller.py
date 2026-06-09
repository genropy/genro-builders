# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""05 — Reactive controller: change an input, the data_controller re-runs.

A data_controller reads ^.start and writes ^.count / ^.quiet via SET/PUT.
Inside a live section the input is changed; the controller re-runs with the
new value and the spans that read its outputs re-render.
"""
from __future__ import annotations

from genro_builders.contrib.html import HtmlBuilder
from genro_builders.contrib.html.examples.reactive.example_app import ExampleApp


class CustomPage(HtmlBuilder):
    @staticmethod
    def init_box(node, start):
        node.SET(".count", start)
        node.PUT(".quiet", node.GET(".count") + 1)

    def main(self, root):
        box = root.body().div(datapath="box")
        box.data_setter(".start", 7)
        box.data_controller(func="init_box", start="^.start", _on_start=True)
        box.span("^.count")
        box.span("^.quiet")


class CustomApp(ExampleApp):
    def change_00_start(self, source, data):
        data.set_item("main.box.start", 20)     # count 7->20, quiet 8->21

    def change_01_start_again(self, source, data):
        data.set_item("main.box.start", 100)    # count 20->100, quiet 21->101


if __name__ == "__main__":
    app = CustomApp((CustomPage(), "output.html"))
    print(app.page.rendered_target)
    app.run()
