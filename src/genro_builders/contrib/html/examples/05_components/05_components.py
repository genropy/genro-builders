# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""05 — Components: reusable composite structures.

What you learn:
    - @component: decorator for handlers with a body (not empty like @element)
    - main_tag: declares the DOM tag for parent validation
    - The handler receives a fresh Bag (comp) and populates it
    - Components are expanded lazily at build time
    - Reuse: call the component multiple times with different parameters

Prerequisites: 04_pointers

Usage:
    python 05_components.py
"""
from __future__ import annotations

from pathlib import Path

from genro_builders.builder import component
from genro_builders.contrib.html import HtmlBuilder
from genro_builders.manager import BuilderManager


class CatalogBuilder(HtmlBuilder):
    """HtmlBuilder extended with a product_card component."""

    @component(main_tag='div')
    def product_card(self, comp, name=None, price=None, description=None, **kwargs):
        """A product card — reusable structure with parameters.

        main_tag='div' tells the validator: "treat me as a div"
        so I can be placed inside body, div, section, etc.
        """
        card = comp.div(_class="card")
        card.h3(name or "Unnamed")
        card.p(price or "", _class="price")
        card.p(description or "")


class ProductCatalog(BuilderManager):
    """Product catalog using the card component."""

    def __init__(self):
        self.page = self.set_builder("page", CatalogBuilder)
        self.run()

    def store(self, data):
        data["products"] = [
            {
                "name": "Wireless Headphones",
                "price": "$79.99",
                "description": "Premium sound, 30h battery.",
            },
            {
                "name": "Mechanical Keyboard",
                "price": "$129.99",
                "description": "Cherry MX switches, RGB backlight.",
            },
            {
                "name": "USB-C Hub",
                "price": "$49.99",
                "description": "7-in-1: HDMI, USB-A, SD, ethernet.",
            },
        ]

    def main(self, source):
        head = source.head()
        head.title("Product Catalog")
        head.style("""
            body { font-family: sans-serif; max-width: 700px; margin: 2em auto; }
            .catalog { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1em; }
            .card { border: 1px solid #ddd; border-radius: 8px; padding: 1em; }
            .card h3 { margin-top: 0; }
            .price { color: #16a34a; font-weight: bold; font-size: 1.2em; }
        """)

        body = source.body()
        body.h1("Product Catalog")

        catalog = body.div(_class="catalog")

        # Reuse the component for each product
        for product in self.reactive_store["products"]:
            catalog.product_card(
                name=product["name"],
                price=product["price"],
                description=product["description"],
            )


app = ProductCatalog()
html = app.page.render()

output = Path(__file__).with_suffix(".html")
output.write_text(html)
print(html)
print(f"\nSaved to {output}")
