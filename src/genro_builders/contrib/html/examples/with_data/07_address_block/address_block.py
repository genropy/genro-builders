# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""07 — Address block: a single component with explicit params. See readme.md."""
from __future__ import annotations

from genro_builders.builder import BuilderHandler, component
from genro_builders.contrib.html import HtmlBuilder


class CommonComponents:
    """Reusable blocks shared across pages (a component mixin)."""

    @component
    def address_block(self, root, company=None, street=None,
                      city=None, zip_code=None):
        card = root.div(class_="address")
        card.strong(company)
        card.div(street)
        card.div(f"{zip_code} {city}")


class CustomPage(HtmlBuilder, CommonComponents):
    def setup(self, data):
        data.set_item("sender.company", "Softwell S.r.l.")
        data.set_item("sender.street", "Via Salvo D'Acquisto 6")
        data.set_item("sender.city", "Milano")
        data.set_item("sender.zip", "20158")

    def main(self, root):
        body = root.body()
        body.h2("Sender")
        # Explicit params saturate the body signature; pointers are
        # resolved by runtime_values before the body runs.
        body.address_block(
            company="^sender.company", street="^sender.street",
            city="^sender.city", zip_code="^sender.zip",
        )
        body.h2("Customer")
        # Same component, literal params: the call site decides the data.
        body.address_block(
            company="ACME Corp", street="123 Main St",
            city="Springfield", zip_code="62704",
        )


if __name__ == "__main__":
    page = CustomPage()
    handler = BuilderHandler()
    handler.add_builder(page)
    page.set_render_target("output.html")
    page.render(pretty=True)
    print(page.rendered_target)
