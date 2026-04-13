# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""10 — Suspend and resume: batched updates for performance.

What you learn:
    - suspend_output(): pause automatic re-rendering
    - resume_output(): flush pending changes in one render
    - Without suspension: N data changes = N renders
    - With suspension: N data changes = 1 render
    - ReactiveManager as the production pattern for reactive apps

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
    """Dashboard with multiple data fields — shows suspend/resume benefit."""

    def __init__(self):
        self.page = self.set_builder("page", CountingBuilder)
        self.run(subscribe=True)

    def store(self, data):
        data["temperature"] = 20
        data["humidity"] = 45
        data["pressure"] = 1013
        data["wind_speed"] = 12

    def main(self, source):
        source.data_setter("temperature", value="^temperature")
        source.data_setter("humidity", value="^humidity")
        source.data_setter("pressure", value="^pressure")
        source.data_setter("wind_speed", value="^wind_speed")

        body = source.body()
        body.h1("Weather Dashboard")
        body.p("^temperature")
        body.p("^humidity")
        body.p("^pressure")
        body.p("^wind_speed")


app = Dashboard()
store = app.reactive_store
render_count[0] = 0  # reset after initial build+render

# --- Without suspension: each change triggers a render ---
print("=== Without suspension ===\n")

store["temperature"] = 25
store["humidity"] = 60
store["pressure"] = 1015
store["wind_speed"] = 8

print(f"4 data changes → {render_count[0]} renders")
print()

# --- With suspension: batch all changes, one render ---
print("=== With suspension ===\n")

render_count[0] = 0

app.page.suspend_output()
store["temperature"] = 30
store["humidity"] = 75
store["pressure"] = 1010
store["wind_speed"] = 15
app.page.resume_output()

print(f"4 data changes (suspended) → {render_count[0]} render")
print()

print("Suspension is essential when updating many fields at once.")
print("Without it, each change triggers a full render cycle.")
