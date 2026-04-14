# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""10 — Explicit render: pull model and render-on-demand.

What you learn:
    - Pull model: data changes do NOT auto-render
    - render() is called explicitly when you want output
    - Multiple data changes → one render() call = efficient batching
    - No need for suspend/resume — batching is natural

Prerequisites: 08_reactive_basics

Usage:
    python 10_suspend_resume.py
"""
from __future__ import annotations

from genro_builders.contrib.html import HtmlBuilder
from genro_builders.manager import ReactiveManager

render_count = [0]
original_render = HtmlBuilder.render


class CountingBuilder(HtmlBuilder):
    """HtmlBuilder that counts how many times render() is called."""

    def render(self, *args, **kwargs):
        render_count[0] += 1
        return original_render(self, *args, **kwargs)


class Dashboard(ReactiveManager):
    """Dashboard showing explicit render pattern."""

    def __init__(self):
        self.page = self.set_builder("page", CountingBuilder)
        self.run(subscribe=True)

    def store(self, data):
        data["temperature"] = 20
        data["humidity"] = 45
        data["pressure"] = 1013
        data["wind_speed"] = 12

    def main(self, source):
        body = source.body()
        body.h1("Weather Dashboard")
        body.p("^temperature")
        body.p("^humidity")
        body.p("^pressure")
        body.p("^wind_speed")


app = Dashboard()
store = app.reactive_store
render_count[0] = 0

# --- Multiple changes, then one render ---
print("=== Pull model: explicit render ===\n")

store["temperature"] = 25
store["humidity"] = 60
store["pressure"] = 1015
store["wind_speed"] = 8

print(f"4 data changes, renders so far: {render_count[0]}")
print("(No auto-render in pull model)\n")

output = app.page.render()
print(f"After explicit render(): {render_count[0]} render total")
assert "25" in output
assert "60" in output
print()

# --- Change + render pattern ---
print("=== Change-then-render pattern ===\n")

render_count[0] = 0

store["temperature"] = 30
store["humidity"] = 75
store["pressure"] = 1010
store["wind_speed"] = 15
output = app.page.render()

print(f"4 changes + 1 render = {render_count[0]} render call")
assert "30" in output
assert "75" in output
print()

print("In pull model, batching is natural — you control when to render.")
print("No suspend/resume needed.")
