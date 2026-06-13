# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""11 — Component recursion: a component that uses itself. See readme.md."""
from __future__ import annotations

from genro_builders.builder import BuilderHandler, component
from genro_builders.contrib.html import HtmlBuilder


class CommonComponents:
    """Reusable blocks shared across pages (a component mixin)."""

    @component
    def treeItem(self, root, node_label=None):
        li = root.li(datapath="." + node_label)
        li.span("^.name")
        # The component calls ITSELF: recursion over the data tree.
        # Termination is data-driven — a leaf has no '.children', the
        # iterate finds an empty collection, zero blocks, the descent
        # stops.
        li.ul().treeItem(iterate="^.children")


class CustomPage(HtmlBuilder, CommonComponents):
    def setup(self, data):
        data.set_item("tree.a.name", "Documents")
        data.set_item("tree.a.children.a1.name", "Invoices")
        data.set_item("tree.a.children.a1.children.x.name", "2026")
        data.set_item("tree.a.children.a2.name", "Contracts")
        data.set_item("tree.b.name", "Pictures")

    def main(self, root):
        body = root.body()
        body.h2("Folders")
        body.ul().treeItem(iterate="^tree")


if __name__ == "__main__":
    page = CustomPage()
    handler = BuilderHandler()
    handler.add_builder(page)
    page.set_render_target("output.html")
    page.render(pretty=True)
    print(page.rendered_target)
