# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""08 — Reactive basics: data_setter, data_formula, subscribe.

What you learn:
    - data_setter: declare a static value in the reactive store
    - data_formula: declare a computed value (re-executes when deps change)
    - subscribe(): activate reactive bindings — data changes trigger re-render
    - Formula dependency chains: topological sort ensures correct order
    - Changing data after subscribe() automatically updates output

Prerequisites: 04_pointers

Usage:
    python 08_reactive_basics.py
"""
from __future__ import annotations

from pathlib import Path

from genro_builders.contrib.html import HtmlBuilder
from genro_builders.manager import ReactiveManager


class PriceCalculator(ReactiveManager):
    """Reactive price calculator: change base_price → net and total update."""

    def __init__(self):
        self.page = self.set_builder("page", HtmlBuilder)
        self.run(subscribe=True)

    def store(self, data):
        data["base_price"] = 100
        data["discount"] = 0.1
        data["tax_rate"] = 0.22

    def main(self, source):
        # Data infrastructure: data_setter for static, data_formula for computed
        source.data_setter("base_price", value="^base_price")
        source.data_setter("discount", value="^discount")
        source.data_setter("tax_rate", value="^tax_rate")

        # Computed: net_price depends on base_price and discount
        source.data_formula(
            "net_price",
            func=lambda base_price, discount: base_price * (1 - discount),
            base_price="^base_price",
            discount="^discount",
        )

        # Computed: total depends on net_price and tax_rate
        # Topological sort ensures net_price is computed before total
        source.data_formula(
            "total",
            func=lambda net_price, tax_rate: round(net_price * (1 + tax_rate), 2),
            net_price="^net_price",
            tax_rate="^tax_rate",
        )

        head = source.head()
        head.title("Price Calculator")
        head.style("""
            body { font-family: sans-serif; max-width: 400px; margin: 2em auto; }
            .result { font-size: 1.3em; color: #16a34a; font-weight: bold; }
            .detail { color: #666; }
        """)

        body = source.body()
        body.h1("Price Calculator")
        body.p("^base_price", _class="detail")
        body.p("^net_price", _class="result")
        body.p("^total", _class="result")


output = Path(__file__).with_suffix(".html")
app = PriceCalculator()
store = app.reactive_store

print("=== Reactive Price Calculator ===\n")
print(f"Initial: base={store['base_price']}, net={store['net_price']}, total={store['total']}")
app.page.render(output=str(output))
print(f"Saved to {output}")

# Change base_price → formulas re-execute → output updates automatically
store["base_price"] = 200
print(f"After change: base={store['base_price']}, net={store['net_price']}, total={store['total']}")
app.page.render(output=str(output))
print(f"Updated {output}")

# Change discount → net_price recalculates → total recalculates
store["discount"] = 0.25
print(f"After discount: base={store['base_price']}, net={store['net_price']}, total={store['total']}")
app.page.render(output=str(output))
print(f"Updated {output}")
