# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""04 — Pointers: declarative data binding with ^pointer syntax.

What you learn:
    - ^pointer syntax: '^key' binds element content to data
    - Data is resolved at render time from the builder's namespace
    - Swap JSON file → different output, same structure
    - Pointer vs inline: inline is static, pointer is resolved from data

Prerequisites: 03_builder_manager

Usage:
    python 04_pointers.py
    python 04_pointers.py product_alt.json
"""
from __future__ import annotations

import sys
from pathlib import Path

from genro_bag import Bag
from genro_bag.resolvers import FileResolver

from genro_builders.contrib.html import HtmlManager

HERE = Path(__file__).parent


class ProductCard(HtmlManager):
    """A product card with data-bound fields."""

    def main(self, source):
        head = source.head()
        head.title("Product Card")
        # FileResolver: pull model — content loaded on demand at render time
        head.style(FileResolver("style.css", base_path=str(HERE)))

        body = source.body()
        page = body.div(_class="page")

        # ^pointer: content resolved from builder's namespace at render time
        page.h2("^name")
        page.p("^price", _class="price")
        page.p("^description")
        page.p("^in_stock", _class="stock")


# Choose data file from command line or default
data_file = sys.argv[1] if len(sys.argv) > 1 else "product.json"

app = ProductCard()
app.local_store("page").fill_from(
    Bag.from_json((HERE / data_file).read_text()),
)
html = app.render()

output = HERE / "04_pointers.html"
output.write_text(html)
print(html)
print(f"\nData: {data_file}")
print(f"Saved to {output}")
