# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""08 — Reactive basics: data_setter, data_formula, pull model.

What you learn:
    - data_setter: declare a static value in the reactive store
    - data_formula: declare a computed value (FormulaResolver, pull model)
    - Formula dependency chains resolve naturally on demand
    - Changing data → re-render shows fresh values
    - Data from external JSON, CSS from external file

Prerequisites: 04_pointers

Usage:
    python 08_reactive_basics.py
"""
from __future__ import annotations

from pathlib import Path

from genro_bag import Bag
from genro_bag.resolvers import FileResolver

from genro_builders.contrib.html import HtmlManager

HERE = Path(__file__).parent


class PriceCalculator(HtmlManager):
    """Reactive price calculator: change base_price → net and total update."""

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
        # FileResolver: pull model — content loaded on demand at render time
        head.style(FileResolver("style.css", base_path=str(HERE)))

        body = source.body()
        page = body.div(_class="page")
        page.h1("Price Calculator")
        page.p("^base_price", _class="detail")
        page.p("^net_price", _class="result")
        page.p("^total", _class="result")


output = HERE / "08_reactive_basics.html"
app = PriceCalculator()
app.local_store("page").fill_from(
    Bag.from_json((HERE / "data.json").read_text()),
)
app.run()
store = app.local_store("page")

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
