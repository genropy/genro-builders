# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""05 — Components: reusable composite structures.

What you learn:
    - @component: decorator for handlers with a body (not empty like @element)
    - main_tag: declares the DOM tag for parent validation
    - The handler receives a fresh Bag (comp) and populates it
    - Components are expanded lazily at build time
    - Reuse: call the component multiple times with different parameters
    - Custom builder extends HtmlBuilder, manager wraps it

Prerequisites: 04_pointers

Usage:
    python 05_components.py
"""
from __future__ import annotations

from pathlib import Path

from genro_builders.builder import component
from genro_builders.contrib.html import HtmlBuilder
from genro_builders.manager import ReactiveManager


class CatalogBuilder(HtmlBuilder):
    """HtmlBuilder extended with a product_card component."""

    @component(main_tag='div')
    def product_card(self, comp, name=None, price=None, description=None, **kwargs):
        """A product card — reusable structure with parameters."""
        card = comp.div(_class="card")
        card.h3(name or "Unnamed")
        card.p(price or "", _class="price")
        card.p(description or "")


class ProductCatalog(ReactiveManager):
    """Product catalog using the card component."""

    def on_init(self):
        self.page = self.register_builder("page", CatalogBuilder)

    def store(self, data):
        data["products"] = [
            {"name": "Wireless Headphones", "price": "$79.99",
             "description": "Premium sound, 30h battery."},
            {"name": "Mechanical Keyboard", "price": "$129.99",
             "description": "Cherry MX switches, RGB backlight."},
            {"name": "USB-C Hub", "price": "$49.99",
             "description": "7-in-1: HDMI, USB-A, SD, ethernet."},
        ]

    def main(self, source):
        head = source.head()
        head.title("Product Catalog")
        head.style("""
            .page { font-family: sans-serif; max-width: 700px; margin: 2em auto;
                    color: #333; background: #fff; padding: 1.5em; border-radius: 8px; }
            .catalog { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1em; }
            .card { border: 1px solid #ddd; border-radius: 8px; padding: 1em; }
            .card h3 { margin-top: 0; color: #1e293b; }
            .price { color: #16a34a; font-weight: bold; font-size: 1.2em; }
            h1 { color: #1e293b; }
        """)

        body = source.body()
        page = body.div(_class="page")
        page.h1("Product Catalog")

        catalog = page.div(_class="catalog")
        for product in self.reactive_store["products"]:
            catalog.product_card(
                name=product["name"],
                price=product["price"],
                description=product["description"],
            )


app = ProductCatalog()
app.run()
html = app.page.render()

output = Path(__file__).with_suffix(".html")
output.write_text(html)
print(html)
print(f"\nSaved to {output}")
