# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""12 — Full App: all patterns combined in a mini e-commerce.

What you learn:
    - Everything together: components, iterate, pointers, reactivity, live REPL
    - Multi-builder: page + sidebar sharing a reactive store
    - @component with main_tag for reusable HTML patterns
    - data_formula for computed values (cart total, item count)
    - data_controller for side effects (write HTML on change)
    - contrib/live for real-time manipulation from REPL

Prerequisites: All previous examples (01-11)

Setup:
    Terminal 1: python 12_full_app.py
    Terminal 2: genro-live connect shop

REPL commands:
    data["cart.item_count"] = 3           # change cart item count
    data["discount_pct"] = 20             # apply 20% discount
    source.h2("Flash Sale!")              # add element to page
    remote.builders()                     # ["page", "sidebar"]

Usage:
    python 12_full_app.py
"""
from __future__ import annotations

import signal
from pathlib import Path

from genro_bag import Bag

from genro_builders.builder import component
from genro_builders.contrib.html import HtmlBuilder
from genro_builders.contrib.live import enable_remote
from genro_builders.manager import ReactiveManager

OUTPUT = Path(__file__).with_suffix(".html")


class ShopBuilder(HtmlBuilder):
    """HtmlBuilder with e-commerce components."""

    @component(main_tag='div', sub_tags='')
    def product_card(self, comp, **kwargs):
        """Product card with data-bound fields."""
        card = comp.div(_class="product-card")
        card.h3("^.?name")
        card.p("^.?price", _class="price")
        card.p("^.?description", _class="desc")

    @component(main_tag='div', sub_tags='')
    def cart_summary(self, comp, **kwargs):
        """Shopping cart summary with computed totals."""
        box = comp.div(_class="cart-summary")
        box.h3("Cart")
        box.p("^cart.item_count", _class="count")
        box.p("^cart.subtotal", _class="subtotal")
        box.p("^cart.discount", _class="discount")
        box.p("^cart.total", _class="total")


class Shop(ReactiveManager):
    """Mini e-commerce: product catalog + cart with live REPL."""

    def __init__(self):
        self.page = self.set_builder("page", ShopBuilder)
        self.sidebar = self.set_builder("sidebar", ShopBuilder)
        self.run(subscribe=True)

    def store(self, data):
        # Products
        products = Bag()
        products.set_item("p0", None, name="Headphones", price="$79", description="30h battery")
        products.set_item("p1", None, name="Keyboard", price="$129", description="Mechanical")
        products.set_item("p2", None, name="Monitor", price="$349", description="4K 144Hz")
        data["products"] = products

        # Cart state
        data["cart.item_count"] = 2
        data["cart.unit_price"] = 79
        data["discount_pct"] = 10

    def main_page(self, source):
        """Page builder: product catalog."""
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

        # Write HTML on any cart change
        source.data_controller(
            func=lambda total: self._write_html(),
            total="^cart.total",
        )

        head = source.head()
        head.title("GenroShop")
        head.style("""
            body { font-family: sans-serif; max-width: 800px; margin: 2em auto; }
            .catalog { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1em; }
            .product-card { border: 1px solid #ddd; border-radius: 8px; padding: 1em; }
            .product-card h3 { margin-top: 0; }
            .price { color: #16a34a; font-weight: bold; }
            .desc { color: #666; }
            .cart-summary { background: #f0f4f8; padding: 1em; border-radius: 8px; margin-top: 1.5em; }
            .total { font-size: 1.3em; font-weight: bold; color: #2563eb; }
        """)

        body = source.body()
        body.h1("GenroShop")

        catalog = body.div(_class="catalog")
        catalog.product_card(iterate="^products")

    def main_sidebar(self, source):
        """Sidebar builder: cart summary."""
        source.body().cart_summary()

    def _write_html(self):
        """Combine page + sidebar into one HTML file."""
        page_html = self.page.render()
        sidebar_html = self.sidebar.render()
        combined = f"{page_html}\n<!-- Sidebar -->\n{sidebar_html}"
        OUTPUT.write_text(combined)


app = Shop()
app._write_html()

server = enable_remote(app, name="shop")

print(f"Shop running on port {server.port}")
print(f"HTML output: {OUTPUT}")
print()
print("Connect: genro-live connect shop")
print()
print("Try:")
print('  data["cart.item_count"] = 5')
print('  data["discount_pct"] = 25')
print('  data["cart.unit_price"] = 129')
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
