# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0

"""Reactive data infrastructure example.

Demonstrates data_setter, data_formula, data_controller, computed
attributes, formula dependency chains with topological sort,
and output suspension for batched updates.

Usage:
    python -m examples.builders.reactive_data_example
"""

from __future__ import annotations

from genro_builders.builders import HtmlBuilder


def basic_formula():
    """data_setter + data_formula + reactive update."""
    print("=== Basic Formula ===")

    builder = HtmlBuilder()
    s = builder.source

    # Static data
    s.data_setter("greeting", value="Hello")

    # Computed data: re-executes when ^greeting changes
    s.data_formula(
        "message",
        func=lambda greeting: f"{greeting}, World!",
        greeting="^greeting",
    )

    # UI bound to computed data
    body = s.body()
    body.h1(value="^message")

    builder.build()
    builder.subscribe()
    print(f"Initial: {builder.output}")

    # Change source data -> formula re-executes -> re-render
    builder.data["greeting"] = "Ciao"
    print(f"After change: {builder.output}")
    print()


def dependency_chain():
    """Formula dependency chain with topological sort."""
    print("=== Dependency Chain ===")

    builder = HtmlBuilder()
    s = builder.source

    s.data_setter("base_price", value=100)
    s.data_setter("discount", value=0.1)
    s.data_setter("tax_rate", value=0.22)

    # Executes first: depends on base_price and discount
    s.data_formula(
        "net_price",
        func=lambda base_price, discount: base_price * (1 - discount),
        base_price="^base_price",
        discount="^discount",
    )

    # Executes second: depends on net_price (computed above)
    s.data_formula(
        "total",
        func=lambda net_price, tax_rate: round(net_price * (1 + tax_rate), 2),
        net_price="^net_price",
        tax_rate="^tax_rate",
    )

    body = s.body()
    body.p(value="^net_price")
    body.p(value="^total")

    builder.build()
    builder.subscribe()
    print(f"Net: {builder.data['net_price']}, Total: {builder.data['total']}")

    # Change base_price -> net_price recalculates -> total recalculates
    builder.data["base_price"] = 200
    print(f"Net: {builder.data['net_price']}, Total: {builder.data['total']}")
    print()


def controller_example():
    """data_controller for side effects."""
    print("=== Controller ===")

    log = []

    builder = HtmlBuilder()
    s = builder.source

    s.data_setter("counter", value=0)

    # Controller: logs every change (no output path)
    s.data_controller(
        func=lambda counter: log.append(f"counter={counter}"),
        counter="^counter",
    )

    body = s.body()
    body.p(value="^counter")

    builder.build()
    builder.subscribe()

    builder.data["counter"] = 1
    builder.data["counter"] = 2
    builder.data["counter"] = 3

    print(f"Log: {log}")
    print()


def suspend_resume():
    """Output suspension for batched updates."""
    print("=== Suspend / Resume ===")

    render_count = [0]
    original_render = HtmlBuilder.render

    class CountingBuilder(HtmlBuilder):
        def render(self, *args, **kwargs):
            render_count[0] += 1
            return original_render(self, *args, **kwargs)

    builder = CountingBuilder()
    s = builder.source

    s.data_setter("a", value=0)
    s.data_setter("b", value=0)
    s.data_setter("c", value=0)

    body = s.body()
    body.p(value="^a")
    body.p(value="^b")
    body.p(value="^c")

    builder.build()
    builder.subscribe()
    render_count[0] = 0  # reset after initial render

    # Without suspension: 3 renders
    builder.data["a"] = 1
    builder.data["b"] = 2
    builder.data["c"] = 3
    renders_without = render_count[0]

    # With suspension: 1 render
    render_count[0] = 0
    builder.suspend_output()
    builder.data["a"] = 10
    builder.data["b"] = 20
    builder.data["c"] = 30
    builder.resume_output()
    renders_with = render_count[0]

    print(f"Without suspension: {renders_without} renders")
    print(f"With suspension: {renders_with} render")
    print()


def computed_attribute():
    """Computed attributes with ^pointer defaults."""
    print("=== Computed Attributes ===")

    builder = HtmlBuilder()
    s = builder.source

    s.data_setter("theme.bg", value="#ffffff")
    s.data_setter("theme.fg", value="#333333")

    body = s.body()
    body.div(
        style=lambda bg="^theme.bg", fg="^theme.fg": f"background:{bg};color:{fg}",
    )

    builder.build()
    builder.subscribe()
    print(f"Output: {builder.output}")

    builder.data["theme.bg"] = "#1a1a2e"
    builder.data["theme.fg"] = "#e0e0e0"
    print(f"After theme change: {builder.output}")
    print()


if __name__ == "__main__":
    basic_formula()
    dependency_chain()
    controller_example()
    suspend_resume()
    computed_attribute()
