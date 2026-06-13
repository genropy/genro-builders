# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""07 — Component live: mutations inside an iterated collection. See readme.md.

The expansion's pointers are never in the pointer_map (by design): the
component node holds ONE coarse subscription on its anchor (``^states``).
Any mutation INSIDE the collection — a field of one item, a new item, a
removed item — must find that reader through the anchor and re-render.
"""
from __future__ import annotations

from genro_builders.builder import component
from genro_builders.contrib.html import HtmlBuilder
from genro_builders.contrib.html.examples.reactive.example_app import ExampleApp


class CommonComponents:
    @component
    def stateRow(self, root, node_label=None):
        row = root.tr(datapath="." + node_label)
        row.td("^.name")
        row.td("^.capital")


class CustomPage(HtmlBuilder, CommonComponents):
    def setup(self, data):
        data.set_item("states.QLD.name", "Queensland")
        data.set_item("states.QLD.capital", "Brisbane")
        data.set_item("states.VIC.name", "Victoria")
        data.set_item("states.VIC.capital", "Melbourne")

    def main(self, root):
        root.body().table().tbody().stateRow(iterate="^states")


class CustomApp(ExampleApp):
    def change_00_update_a_field(self, source, data):
        # No reader registered on this exact path: the component's anchor
        # subscription (main.states) must catch it.
        data.set_item("main.states.QLD.capital", "BRISBANE")

    def change_01_add_an_item(self, source, data):
        data.set_item("main.states.NSW.name", "New South Wales")
        data.set_item("main.states.NSW.capital", "Sydney")

    def change_02_remove_an_item(self, source, data):
        data.del_item("main.states.VIC")


if __name__ == "__main__":
    app = CustomApp((CustomPage(name="main"), "output.html"))
    print(app.page.rendered_target)
    app.run()
