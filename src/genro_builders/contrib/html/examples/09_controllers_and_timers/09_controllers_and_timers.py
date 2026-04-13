# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""09 — Controllers: side effects on data changes.

What you learn:
    - data_controller: runs a function for side effects (no data output)
    - Unlike data_formula, a controller does not write to a data path
    - Controllers fire on every change of their dependencies
    - Use cases: logging, validation, notifications, syncing

Note on _delay and _interval:
    data_formula supports _delay (debounce) and _interval (periodic),
    but these require an async event loop (asyncio.run, Textual, ASGI).
    See example 11_live_repl for async usage.

Prerequisites: 08_reactive_basics

Usage:
    python 09_controllers_and_timers.py
"""
from __future__ import annotations

from genro_builders.contrib.html import HtmlBuilder
from genro_builders.manager import ReactiveManager

# --- data_controller: side effects ---

print("=== data_controller: logging side effects ===\n")

log: list[str] = []


class LoggingApp(ReactiveManager):
    """Tracks every data change via data_controller."""

    def __init__(self):
        self.page = self.set_builder("page", HtmlBuilder)
        self.run(subscribe=True)

    def store(self, data):
        data["counter"] = 0
        data["name"] = "Alice"

    def main(self, source):
        # Controller on counter: logs every change
        source.data_controller(
            func=lambda counter: log.append(f"counter changed to {counter}"),
            counter="^counter",
        )

        # Controller on name: logs every change
        source.data_controller(
            func=lambda name: log.append(f"name changed to '{name}'"),
            name="^name",
        )

        body = source.body()
        body.p("^counter")
        body.p("^name")


app = LoggingApp()
store = app.reactive_store

# Initial values trigger controllers during build
print(f"After build: {log}")
log.clear()

# Change counter 3 times → 3 controller calls
store["counter"] = 1
store["counter"] = 2
store["counter"] = 3
print(f"After 3 counter changes: {log}")
log.clear()

# Change name → name controller fires
store["name"] = "Bob"
print(f"After name change: {log}")
log.clear()
print()


# --- data_controller with multiple dependencies ---

print("=== Controller with multiple dependencies ===\n")

alerts: list[str] = []


class AlertApp(ReactiveManager):
    """Controller that fires when any of its dependencies change."""

    def __init__(self):
        self.page = self.set_builder("page", HtmlBuilder)
        self.run(subscribe=True)

    def store(self, data):
        data["temperature"] = 20
        data["threshold"] = 30

    def main(self, source):
        # Controller watching two values — fires when either changes
        source.data_controller(
            func=lambda temperature, threshold: alerts.append(
                f"ALERT: {temperature}°C" if temperature > threshold
                else f"OK: {temperature}°C"
            ),
            temperature="^temperature",
            threshold="^threshold",
        )
        source.body().p("^temperature")


app2 = AlertApp()
store2 = app2.reactive_store
alerts.clear()

store2["temperature"] = 25
store2["temperature"] = 35  # exceeds threshold
store2["threshold"] = 40    # raise threshold → OK again
store2["temperature"] = 38  # still under new threshold

print(f"Alerts: {alerts}")
print("\ndata_controller is the reactive hook for side effects.")
print("It complements data_formula (which computes and stores values).")
