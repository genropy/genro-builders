# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""09 — Active cache and data subscriptions: periodic refresh and side effects.

What you learn:
    - _cache_time on data_formula: periodic background refresh (active cache)
    - data.subscribe(): react to data changes with side effects
    - Pull model: formulas compute on-demand, active cache pushes updates
    - Side effects (logging, alerts) use data.subscribe, not the builder
    - Data from external JSON files

Prerequisites: 08_reactive_basics

Usage:
    python 09_controllers_and_timers.py
"""
from __future__ import annotations

from pathlib import Path

from genro_bag import Bag

from genro_builders.contrib.html import HtmlBuilder
from genro_builders.manager import ReactiveManager

HERE = Path(__file__).parent

# --- Part 1: data.subscribe for side effects ---

print("=== data.subscribe: logging side effects ===\n")

log: list[str] = []


class LoggingApp(ReactiveManager):
    """Tracks data changes via data.subscribe (not via the builder)."""

    def on_init(self):
        self.page = self.register_builder("page", HtmlBuilder)
        self.run(subscribe=True)
        self.global_store.subscribe(
            "logger",
            any=lambda pathlist=None, **kw: log.append(
                f"{'.'.join(str(p) for p in pathlist)} changed" if pathlist else "?"
            ),
        )

    def main(self, source):
        body = source.body()
        body.p("^counter")
        body.p("^name")


app = LoggingApp()
app.local_store("page").fill_from(
    Bag.from_json((HERE / "data.json").read_text()),
)
app.page.build()
store = app.local_store("page")
log.clear()

store["counter"] = 1
store["counter"] = 2
store["counter"] = 3
print(f"After 3 counter changes: {log}")
log.clear()

store["name"] = "Bob"
print(f"After name change: {log}")
log.clear()
print()


# --- Part 2: data_formula with _cache_time (active cache) ---

print("=== data_formula with active cache ===\n")

print("Active cache requires an async event loop.")
print("Use _cache_time=-N for periodic background refresh.")
print("See example 11_live_repl for async usage.\n")


class PriceApp(ReactiveManager):
    """Formulas compute on demand — no _cache_time needed for sync."""

    def on_init(self):
        self.page = self.register_builder("page", HtmlBuilder)
        self.run(subscribe=True)

    def main(self, source):
        source.data_formula(
            "total",
            func=lambda price, tax_rate: round(price * (1 + tax_rate), 2),
            price="^price",
            tax_rate="^tax_rate",
        )
        body = source.body()
        body.p("^total")


app2 = PriceApp()
app2.local_store("page").fill_from(
    Bag.from_json((HERE / "price_data.json").read_text()),
)
app2.page.build()
store2 = app2.local_store("page")
print(f"Initial total: {store2['total']}")

store2["price"] = 200
print(f"After price change: {store2['total']}")

store2["tax_rate"] = 0.10
print(f"After tax change: {store2['total']}")
print()

print("data.subscribe() replaces data_controller for side effects.")
print("data_formula with _cache_time replaces _interval for periodic updates.")
