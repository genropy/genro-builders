# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""13 — Row logic: the rules of the rows are rules of MUTATION. See readme.md.

An iterated body declares dataFormula rules; the expansion walk
CATALOGS them (trigger path -> rule node, per row) and never computes
at render: the loaded document is trusted as-is. The rules fire in the
data-event cascade:

- a row binding (qty) fires THAT row;
- a shared binding (the header exchange rate) resolves to the same
  path for every row: one event recomputes them all;
- the writes cascade (total -> converted) like any data-element.
"""
from __future__ import annotations

from genro_builders.builder import BuilderHandler, TargetWrapper, component
from genro_builders.contrib.html import HtmlBuilder


class Probe(TargetWrapper):
    accepts_partial = True
    render_opts = {"include_datapath": True}

    def __init__(self):
        self.batches = []

    def full(self, document):
        self.full_html = document

    def partial(self, patches):
        self.batches.append(patches)


class CustomPage(HtmlBuilder):
    @component
    def orderRow(self, root, node_label=None):
        row = root.div(datapath="." + node_label)
        row.input(value="^.qty", dtype="L")
        row.input(value="^.price", dtype="N")
        row.dataFormula(destination=".total", func="row_total",
                         qty="^.qty", price="^.price")
        row.dataFormula(destination=".converted", func="convert",
                         total="^.total", rate="^header.rate")
        row.span("${total} / ${converted}", total="^.total",
                 converted="^.converted")

    def setup(self, data):
        data.set_item("header.rate", 0.89)
        for label, qty, price in (("r1", 2, 10), ("r2", 3, 5)):
            data.set_item(f"rows.{label}.qty", qty)
            data.set_item(f"rows.{label}.price", price)
            # The document loads COMPLETE: totals trusted, no render
            # recompute.
            data.set_item(f"rows.{label}.total", qty * price)
            data.set_item(f"rows.{label}.converted",
                          round(qty * price * 0.89, 2))

    def main(self, root):
        root.body().orderRow(iterate="^rows")

    @staticmethod
    def row_total(qty, price):
        if qty is None or price is None:
            return None
        return qty * price

    @staticmethod
    def convert(total, rate):
        if total is None or rate is None:
            return None
        return round(float(total) * float(rate), 2)


if __name__ == "__main__":
    page = CustomPage(name="main")
    probe = Probe()
    page.set_render_target(probe)
    handler = BuilderHandler(application=object())
    handler.add_builder(page)
    handler.activate()

    # Loaded values untouched by the render (trusted document).
    assert handler.data["main.rows.r1.total"] == 20
    assert handler.data["main.rows.r1.converted"] == 17.8

    # Row mutation: THAT row recomputes, and the rule chain cascades
    # (qty -> total -> converted). The sibling row never moves.
    with handler.live():
        handler.data.set_item("main.rows.r1.qty", 7)
    assert handler.data["main.rows.r1.total"] == 70
    assert handler.data["main.rows.r1.converted"] == 62.3
    assert handler.data["main.rows.r2.total"] == 15

    # Header mutation: the shared binding fires EVERY row's rule; the
    # totals stay put (a rate change converts, it does not re-price).
    with handler.live():
        handler.data.set_item("main.header.rate", 0.76)
    assert handler.data["main.rows.r1.converted"] == 53.2
    assert handler.data["main.rows.r2.converted"] == 11.4
    assert handler.data["main.rows.r1.total"] == 70

    print("rows:", {
        label: (handler.data[f"main.rows.{label}.total"],
                handler.data[f"main.rows.{label}.converted"])
        for label in ("r1", "r2")
    })
