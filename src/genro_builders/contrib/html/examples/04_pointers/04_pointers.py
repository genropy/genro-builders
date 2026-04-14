# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""04 — Pointers: declarative data binding with ^pointer syntax.

What you learn:
    - ^pointer syntax: '^key' as first arg binds element content to data
    - Data is resolved at render time from the reactive store
    - Changing data produces different output on next render
    - Pointer vs inline: inline is static, pointer is resolved from data

Prerequisites: 03_builder_manager

Usage:
    python 04_pointers.py
"""
from __future__ import annotations

from pathlib import Path

from genro_builders.contrib.html import HtmlManager


class ProductCard(HtmlManager):
    """A product card with data-bound fields."""

    def store(self, data):
        data["name"] = "Wireless Headphones"
        data["price"] = "$79.99"
        data["description"] = "Premium sound quality with 30-hour battery life."
        data["in_stock"] = "In Stock"

    def main(self, source):
        head = source.head()
        head.title("Product Card")
        head.style("""
            .page { font-family: sans-serif; max-width: 400px; margin: 2em auto;
                    color: #333; background: #fff; padding: 1.5em; border-radius: 8px; }
            .price { font-size: 1.5em; color: #16a34a; font-weight: bold; }
            .stock { color: #666; font-size: 0.9em; }
            h2 { color: #1e293b; }
        """)

        body = source.body()
        page = body.div(_class="page")

        # ^pointer as first arg: content is resolved from reactive_store
        page.h2("^name")
        page.p("^price", _class="price")
        page.p("^description")
        page.p("^in_stock", _class="stock")


# First render — original data
app = ProductCard()
html1 = app.render()

output = Path(__file__).with_suffix(".html")
output.write_text(html1)
print("=== Original ===")
print(html1)

# Change data → next render shows new values (pull model)
app.reactive_store["name"] = "Studio Monitor Speakers"
app.reactive_store["price"] = "$249.99"
app.reactive_store["description"] = "Flat frequency response for accurate mixing."
app.reactive_store["in_stock"] = "Pre-order"

html2 = app.render()
print("\n=== After data change ===")
print(html2)

output.write_text(html2)
print(f"\nSaved to {output}")
