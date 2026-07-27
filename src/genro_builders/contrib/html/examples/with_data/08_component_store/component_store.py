# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""08 — Component store: the component anchored to a record. See readme.md."""
from __future__ import annotations

from genro_builders.builder import component
from genro_builders.contrib.html import HtmlBuilder


class CommonComponents:
    """Reusable blocks shared across pages (a component mixin)."""

    @component
    def addressBlock(self, root, **kwargs):
        # The body reads the record through relative pointers, anchored
        # by the caller's ``store``; the call's other attributes flow in
        # as kwargs and the AUTHOR routes them — here onto the card.
        card = root.div(**kwargs)
        card.strong("^.company")
        card.div("^.street")
        card.div("${z} ${c}", z="^.zip", c="^.city")


class CustomPage(HtmlBuilder, CommonComponents):
    def setup(self, data):
        data.set_item("sender.company", "Softwell S.r.l.")
        data.set_item("sender.street", "Via Salvo D'Acquisto 6")
        data.set_item("sender.city", "Milano")
        data.set_item("sender.zip", "20158")
        data.set_item("customer.company", "ACME Corp")
        data.set_item("customer.street", "123 Main St")
        data.set_item("customer.city", "Springfield")
        data.set_item("customer.zip", "62704")

    def main(self, root):
        body = root.body()
        body.h2("Sender")
        # ``store`` is the component's data anchor: the SAME body renders
        # a different block depending on the record it is anchored to.
        body.addressBlock(store="^sender", class_="address")
        body.h2("Customer")
        body.addressBlock(store="^customer", class_="address compact")


if __name__ == "__main__":
    page = CustomPage()
    page.create()
    page.set_render_target("output.html")
    page.render(pretty=True)
    print(page.rendered_target)
