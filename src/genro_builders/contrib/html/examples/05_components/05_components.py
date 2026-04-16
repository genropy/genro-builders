# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""05 — Components: reusable composite structures.

What you learn:
    - @component: decorator for handlers with a body (not empty like @element)
    - main_tag: declares the DOM tag for parent validation
    - The handler receives a fresh Bag (comp) and populates it
    - Components are expanded lazily at build time
    - Reuse: call the component multiple times with different parameters
    - Data from external JSON, CSS from external file

Prerequisites: 04_pointers

Usage:
    python 05_components.py
"""
from __future__ import annotations

import json
from pathlib import Path

from genro_bag.resolvers import FileResolver

from genro_builders.builder import component
from genro_builders.contrib.html import HtmlBuilder
from genro_builders.manager import ReactiveManager

HERE = Path(__file__).parent


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

    def main(self, source):
        head = source.head()
        head.title("Product Catalog")
        # FileResolver: pull model — content loaded on demand at render time
        head.style(FileResolver("style.css", base_path=str(HERE)))

        body = source.body()
        page = body.div(_class="page")
        page.h1("Product Catalog")

        catalog = page.div(_class="catalog")
        for product in self.local_store()["products"]:
            catalog.product_card(**product)


app = ProductCatalog()
products = json.loads((HERE / "products.json").read_text())
app.local_store("page")["products"] = products
app.run()
html = app.page.render()

output = HERE / "05_components.html"
output.write_text(html)
print(html)
print(f"\nSaved to {output}")
