# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""09 — Component iterate: one expansion per child of a collection. See readme.md."""
from __future__ import annotations

from genro_builders.builder import BuilderHandler, component
from genro_builders.contrib.html import HtmlBuilder


class CommonComponents:
    """Reusable blocks shared across pages (a component mixin)."""

    @component
    def state_row(self, root, node_label=None):
        # One row per item: the renderer passes ONLY the item's label;
        # the body anchors its root to that item (relative to the
        # collection the caller iterated) and reads it with relative
        # pointers.
        row = root.tr(datapath="." + node_label)
        row.td("^.name")
        row.td("^.capital")


class CustomPage(HtmlBuilder, CommonComponents):
    def setup(self, data):
        data.set_item("states.QLD.name", "Queensland")
        data.set_item("states.QLD.capital", "Brisbane")
        data.set_item("states.VIC.name", "Victoria")
        data.set_item("states.VIC.capital", "Melbourne")
        data.set_item("states.NSW.name", "New South Wales")
        data.set_item("states.NSW.capital", "Sydney")

    def main(self, root):
        body = root.body()
        body.h2("Australian states")
        table = body.table()
        tbody = table.tbody()
        # One source node; at render time, one <tr> per child of ^states.
        tbody.state_row(iterate="^states")


if __name__ == "__main__":
    page = CustomPage()
    handler = BuilderHandler()
    handler.add_builder(page)
    page.set_render_target("output.html")
    page.render(pretty=True)
    print(page.rendered_target)
