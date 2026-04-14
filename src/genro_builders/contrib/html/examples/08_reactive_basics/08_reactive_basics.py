# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""08 — Reactive basics: data_setter, data_formula, pull model.

What you learn:
    - data_setter: declare a static value in the reactive store
    - data_formula: declare a computed value (FormulaResolver, pull model)
    - Formula dependency chains resolve naturally on demand
    - Changing data → re-render shows fresh values

Prerequisites: 04_pointers

Usage:
    python 08_reactive_basics.py
"""
from __future__ import annotations

from pathlib import Path

from genro_builders.contrib.html import HtmlManager


class PriceCalculator(HtmlManager):
    """Reactive price calculator: change base_price → net and total update."""

    def store(self, data):
        data["base_price"] = 100
        data["discount"] = 0.1
        data["tax_rate"] = 0.22

    def main(self, source):
        source.data_setter("base_price", value="^base_price")
        source.data_setter("discount", value="^discount")
        source.data_setter("tax_rate", value="^tax_rate")

        source.data_formula(
            "net_price",
            func=lambda base_price, discount: base_price * (1 - discount),
            base_price="^base_price",
            discount="^discount",
        )
        source.data_formula(
            "total",
            func=lambda net_price, tax_rate: round(net_price * (1 + tax_rate), 2),
            net_price="^net_price",
            tax_rate="^tax_rate",
        )

        head = source.head()
        head.title("Price Calculator")
        head.style("""
            .page { font-family: sans-serif; max-width: 400px; margin: 2em auto;
                    color: #333; background: #fff; padding: 1.5em; border-radius: 8px; }
            .result { font-size: 1.3em; color: #16a34a; font-weight: bold; }
            .detail { color: #666; }
            h1 { color: #1e293b; }
        """)

        body = source.body()
        page = body.div(_class="page")
        page.h1("Price Calculator")
        page.p("^base_price", _class="detail")
        page.p("^net_price", _class="result")
        page.p("^total", _class="result")


output = Path(__file__).with_suffix(".html")
app = PriceCalculator()
app.run()
store = app.reactive_store

print("=== Reactive Price Calculator ===\n")
print(f"Initial: base={store['base_price']}, net={store['net_price']}, total={store['total']}")
app.render(output=str(output))
print(f"Saved to {output}")

store["base_price"] = 200
print(f"After change: base={store['base_price']}, net={store['net_price']}, total={store['total']}")
app.render(output=str(output))
print(f"Updated {output}")

store["discount"] = 0.25
print(f"After discount: base={store['base_price']}, net={store['net_price']}, total={store['total']}")
app.render(output=str(output))
print(f"Updated {output}")
