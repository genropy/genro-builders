# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""10 — Component nesting: components inside components. See readme.md."""
from __future__ import annotations

from genro_builders.builder import BuilderHandler, component
from genro_builders.contrib.html import HtmlBuilder


class CommonComponents:
    """Reusable blocks shared across pages (a component mixin)."""

    @component
    def city_item(self, root, node_label=None):
        li = root.li(datapath="." + node_label)
        li.span("^.name")

    @component
    def state_card(self, root, node_label=None):
        card = root.div(datapath="." + node_label, class_="state")
        card.h3("^.name")
        # A component used INSIDE a component's body: the inner iterate
        # is RELATIVE — '^.cities' composes against this card's item.
        card.ul().city_item(iterate="^.cities")


class CustomPage(HtmlBuilder, CommonComponents):
    def setup(self, data):
        data.set_item("states.QLD.name", "Queensland")
        data.set_item("states.QLD.cities.bri.name", "Brisbane")
        data.set_item("states.QLD.cities.cns.name", "Cairns")
        data.set_item("states.VIC.name", "Victoria")
        data.set_item("states.VIC.cities.mel.name", "Melbourne")
        data.set_item("states.VIC.cities.gee.name", "Geelong")

    def main(self, root):
        body = root.body()
        body.h2("States and cities")
        # One source node; two nested levels of expansion at render time.
        body.state_card(iterate="^states")


if __name__ == "__main__":
    page = CustomPage()
    handler = BuilderHandler()
    handler.add_builder(page)
    page.set_render_target("output.html")
    page.render(pretty=True)
    print(page.rendered_target)
