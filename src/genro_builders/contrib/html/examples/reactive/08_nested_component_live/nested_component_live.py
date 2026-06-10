# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""08 — Nested component live: deep mutations, one subscription. See readme.md.

Nested components register nothing: the OUTERMOST component node holds
the only subscription (its anchor, ``^states``). Mutations at ANY depth
inside the collection — a city's field two expansion levels down, a new
city, a whole new state — reach that reader by prefix and re-render.
"""
from __future__ import annotations

from genro_builders.builder import component
from genro_builders.contrib.html import HtmlBuilder
from genro_builders.contrib.html.examples.reactive.example_app import ExampleApp


class CommonComponents:
    @component
    def city_item(self, root, node_label=None):
        li = root.li(datapath="." + node_label)
        li.span("^.name")

    @component
    def state_card(self, root, node_label=None):
        card = root.div(datapath="." + node_label, class_="state")
        card.h3("^.name")
        card.ul().city_item(iterate="^.cities")


class CustomPage(HtmlBuilder, CommonComponents):
    def setup(self, data):
        data.set_item("states.QLD.name", "Queensland")
        data.set_item("states.QLD.cities.bri.name", "Brisbane")

    def main(self, root):
        root.body().state_card(iterate="^states")


class CustomApp(ExampleApp):
    def change_00_rename_a_city(self, source, data):
        # Two expansion levels under the anchor: no reader registered
        # anywhere near this path.
        data.set_item("main.states.QLD.cities.bri.name", "BRISBANE")

    def change_01_add_a_city(self, source, data):
        data.set_item("main.states.QLD.cities.cns.name", "Cairns")

    def change_02_add_a_state_with_cities(self, source, data):
        data.set_item("main.states.VIC.name", "Victoria")
        data.set_item("main.states.VIC.cities.mel.name", "Melbourne")

    def change_03_remove_a_city(self, source, data):
        data.del_item("main.states.QLD.cities.bri")


if __name__ == "__main__":
    app = CustomApp((CustomPage(name="main"), "output.html"))
    print(app.page.rendered_target)
    app.run()
