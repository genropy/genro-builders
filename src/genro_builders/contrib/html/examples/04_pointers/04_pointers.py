# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""04 — Pointers: declarative data binding with ^pointer syntax.

What you learn:
    - ^pointer syntax: '^key' as first arg binds element content to data
    - Data is resolved at build time from the reactive store
    - Changing data and rebuilding produces different output
    - Pointer vs inline: inline is static, pointer is resolved from data

Prerequisites: 03_builder_manager

Usage:
    python 04_pointers.py
"""
from __future__ import annotations

from pathlib import Path

from genro_builders.contrib.html import HtmlBuilder
from genro_builders.manager import BuilderManager


class ProductCard(BuilderManager):
    """A product card with data-bound fields."""

    def __init__(self):
        self.page = self.set_builder("page", HtmlBuilder)
        self.run()

    def store(self, data):
        data["name"] = "Wireless Headphones"
        data["price"] = "$79.99"
        data["description"] = "Premium sound quality with 30-hour battery life."
        data["in_stock"] = "In Stock"

    def main(self, source):
        head = source.head()
        head.title("Product Card")
        head.style("""
            body { font-family: sans-serif; max-width: 400px; margin: 2em auto; }
            .card { border: 1px solid #ddd; border-radius: 8px; padding: 1.5em; }
            .price { font-size: 1.5em; color: #16a34a; font-weight: bold; }
            .stock { color: #666; font-size: 0.9em; }
        """)

        body = source.body()
        card = body.div(_class="card")

        # ^pointer as first arg: content is resolved from reactive_store
        card.h2("^name")
        card.p("^price", _class="price")
        card.p("^description")
        card.p("^in_stock", _class="stock")


# First render — original data
app = ProductCard()
html1 = app.page.render()

output = Path(__file__).with_suffix(".html")
output.write_text(html1)
print("=== Original ===")
print(html1)

# Change data and rebuild — pointers resolve to new values
app.reactive_store["name"] = "Studio Monitor Speakers"
app.reactive_store["price"] = "$249.99"
app.reactive_store["description"] = "Flat frequency response for accurate mixing."
app.reactive_store["in_stock"] = "Pre-order"
app.page.build()

html2 = app.page.render()
print("\n=== After data change + rebuild ===")
print(html2)

output.write_text(html2)
print(f"\nSaved to {output}")
