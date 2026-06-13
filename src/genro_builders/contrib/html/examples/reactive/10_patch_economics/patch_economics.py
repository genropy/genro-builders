# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""10 — Patch economics: measuring the partial render. See readme.md.

A dashboard-shaped page (scattered fields, a computed total, a 40-row
iterated table) instrumented with a metrics wrapper: every batch is
logged as patch ids and byte sizes. The committed metrics.json IS the
measurement the optimization decisions are based on — and the diff
net keeps it honest.
"""
from __future__ import annotations

import json
from pathlib import Path

from genro_bag import Bag

from genro_builders.builder import BuilderHandler, TargetWrapper, component
from genro_builders.contrib.html import HtmlBuilder

ROWS = 40


class Metrics(TargetWrapper):
    """Logs every batch as (id, bytes); writes the document on full."""

    accepts_partial = True
    render_opts = {"include_datapath": True}

    def __init__(self, document_path, metrics_path):
        self.document_path = Path(document_path)
        self.metrics_path = Path(metrics_path)
        self.scenarios: list[dict] = []

    def full(self, document):
        self.document_path.write_text(document, encoding="utf-8")

    def partial(self, patches):
        self.scenarios.append({
            "patches": [
                # value-only cell patches carry no html: their cost is
                # the value text itself
                {"id": p["id"],
                 "bytes": len(p.get("html") or str(p.get("value", "")))}
                for p in patches
            ],
        })
        self.metrics_path.write_text(
            json.dumps(self.scenarios, indent=2), encoding="utf-8",
        )


class CommonComponents:
    @component
    def itemRow(self, root, node_label=None):
        tr = root.tr(datapath="." + node_label)
        tr.td("^.sku")
        tr.td("^.qty")
        tr.td("^.price")


class CustomPage(HtmlBuilder, CommonComponents):
    @staticmethod
    def grand_total(rows):
        return sum(
            row.value["qty"] * row.value["price"] for row in rows.nodes
        )

    def setup(self, data):
        data.set_item("customer", "ACME Corp")
        data.set_item("status", "draft")
        for n in range(ROWS):
            data.set_item(f"rows.r{n:03d}.sku", f"SKU-{n:03d}")
            data.set_item(f"rows.r{n:03d}.qty", 1 + n % 5)
            data.set_item(f"rows.r{n:03d}.price", 10.0)

    def main(self, root):
        body = root.body()
        body.h1("^customer")
        body.div("^status")
        body.dataFormula(
            destination="total", func="grand_total",
            rows="^rows", _on_start=True,
        )
        body.div("^total", class_="total")
        body.table().tbody().itemRow(iterate="^rows")


if __name__ == "__main__":
    wrapper = Metrics("output.html", "metrics.json")
    page = CustomPage(name="main")
    page.set_render_target(wrapper)
    handler = BuilderHandler(application=object())
    handler.add_builder(page)
    handler.activate()

    with handler.live():
        # Scenario 1: one scattered field.
        handler.data.set_item("main.customer", "ACME Corp Intl")

    with handler.live():
        # Scenario 2: one field of ONE row out of 40 — the whole-table
        # patch this produces is the measured cost that motivates the
        # per-row refinement; the formula cascade adds the total patch.
        handler.data.set_item("main.rows.r000.qty", 99)

    with handler.live():
        # Scenario 3: a new row (plus the cascading total). The record
        # is composed first and attached in ONE write: the cascade fires
        # per logical mutation, and a strict formula must never see a
        # half-written row.
        record = Bag({"sku": "SKU-NEW", "qty": 1, "price": 5.0})
        handler.data.set_item(f"main.rows.r{ROWS:03d}", record)

    with handler.live():
        # Scenario 4: three scattered mutations in one section.
        handler.data.set_item("main.customer", "ACME Corp Global")
        handler.data.set_item("main.status", "confirmed")
        handler.data.set_item("main.rows.r001.qty", 7)

    print(json.dumps(wrapper.scenarios, indent=2))
