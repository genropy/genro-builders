# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""12 — Full App: all patterns combined in a mini e-commerce.

What you learn:
    - Everything together: components, iterate, pointers, reactivity, live REPL
    - Multi-builder: page + sidebar sharing a global store
    - @component with main_tag for reusable HTML patterns
    - data_formula for computed values (cart total, item count)
    - data.subscribe for side effects (write HTML on change)
    - Data and CSS from external files

Prerequisites: All previous examples (01-11)

Setup:
    Terminal 1: python 12_full_app.py
    Terminal 2: genro-live connect shop

Usage:
    python 12_full_app.py
"""
from __future__ import annotations

import signal
from pathlib import Path

from genro_bag import Bag
from genro_bag.resolvers import FileResolver

from genro_builders.builder import component
from genro_builders.contrib.html import HtmlBuilder
from genro_builders.contrib.live import enable_remote
from genro_builders.manager import ReactiveManager

HERE = Path(__file__).parent
OUTPUT = HERE / "12_full_app.html"


class ShopBuilder(HtmlBuilder):
    """HtmlBuilder with e-commerce components."""

    @component(main_tag='div', sub_tags='')
    def product_card(self, comp, **kwargs):
        card = comp.div(_class="product-card")
        card.h3("^.?name")
        card.p("^.?price", _class="price")
        card.p("^.?description", _class="desc")

    @component(main_tag='div', sub_tags='')
    def cart_summary(self, comp, **kwargs):
        box = comp.div(_class="cart-summary")
        box.h3("Cart")
        box.p("^cart.item_count", _class="count")
        box.p("^cart.subtotal", _class="subtotal")
        box.p("^cart.discount", _class="discount")
        box.p("^cart.total", _class="total")


class Shop(ReactiveManager):
    """Mini e-commerce: product catalog + cart with live REPL."""

    def on_init(self):
        self.page = self.register_builder("page", ShopBuilder)
        self.sidebar = self.register_builder("sidebar", ShopBuilder)
        self.run(subscribe=True)

    def on_data_changed(self, impacted):
        """Re-render impacted builders and write combined HTML."""
        self._write_html()

    def main_page(self, source):
        # Computed cart values
        source.data_formula(
            "cart.subtotal",
            func=lambda count, price: count * price,
            count="^cart.item_count",
            price="^cart.unit_price",
        )
        source.data_formula(
            "cart.discount",
            func=lambda subtotal, pct: round(subtotal * pct / 100, 2),
            subtotal="^cart.subtotal",
            pct="^discount_pct",
        )
        source.data_formula(
            "cart.total",
            func=lambda subtotal, discount: round(subtotal - discount, 2),
            subtotal="^cart.subtotal",
            discount="^cart.discount",
        )

        head = source.head()
        head.title("GenroShop")
        # FileResolver: pull model — content loaded on demand at render time
        head.style(FileResolver("style.css", base_path=str(HERE)))

        body = source.body()
        body.h1("GenroShop")

        catalog = body.div(_class="catalog")
        catalog.product_card(iterate="^products")

    def main_sidebar(self, source):
        source.body().cart_summary()

    def _write_html(self):
        page_html = self.page.render()
        sidebar_html = self.sidebar.render()
        combined = f"{page_html}\n<!-- Sidebar -->\n{sidebar_html}"
        OUTPUT.write_text(combined)


app = Shop()

# Load data from external files
# products.json is Bag node format → FileResolver with as_bag=True
app.local_store("page").set_resolver(
    "products", FileResolver("products.json", as_bag=True, base_path=str(HERE)),
)
# cart.json is flat dict → fill_from spreads keys into local_store
app.local_store("page").fill_from(
    Bag.from_json((HERE / "cart.json").read_text()),
)
app.page.build()
app._write_html()

server = enable_remote(app, name="shop")

print(f"Shop running on port {server.port}")
print(f"HTML output: {OUTPUT}")
print()
print("Connect: genro-live connect shop")
print()
print("Try:")
print('  data["page.cart.item_count"] = 5')
print('  data["page.discount_pct"] = 25')
print('  data["page.cart.unit_price"] = 129')
print()
print("Press Ctrl+C to stop.")

try:
    signal.pause()
except KeyboardInterrupt:
    print("\nStopping...")
finally:
    server.stop()
    from genro_builders.contrib.live._registry import LiveRegistry
    LiveRegistry().unregister("shop")
    print("Done.")
