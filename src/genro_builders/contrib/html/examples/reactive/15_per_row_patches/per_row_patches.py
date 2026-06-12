# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""15 — Per-row patches: the iterate block updates one row at a time.

The data events under an iterate anchor classify PER ROW (path
arithmetic: the residual's first segment names the row); the flush
patches the single block, addressed by derived identity
(``<base>.<label>.1``):

- a row value changes      -> one ``replace`` of that block;
- a row is born (any spot) -> one ``insert``, anchored before the
  NEXT row's block (bag order — identity is not position);
- a row dies               -> one ``remove`` (derived id: arithmetic,
  no capture needed), its writeback entries purged with it;
- a shared binding floods MORE than ``ROW_COALESCE_LIMIT`` rows in
  one flush -> the per-row patches coalesce back into the enclosing
  container replace (one fragment beats thousands of patches).

ORACLE: every per-row fragment must appear verbatim in a full render
of the same state — patching by row can never diverge from the truth.
"""
from __future__ import annotations

from genro_bag import Bag
from genro_builders.builder import BuilderHandler, TargetWrapper, component
from genro_builders.builder.data_handler import ROW_COALESCE_LIMIT
from genro_builders.contrib.html import HtmlBuilder

ROWS = ROW_COALESCE_LIMIT + 10           # enough to trip the coalescence


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
    def order_row(self, root, node_label=None):
        row = root.div(datapath="." + node_label)
        row.input(value="^.qty", dtype="L")
        row.span("^.converted")
        row.data_formula(destination=".total", func="row_total",
                         qty="^.qty", price="^.price")
        row.data_formula(destination=".converted", func="convert",
                         total="^.total", rate="^header.rate")

    def setup(self, data):
        data.set_item("header.rate", 0.5)
        for n in range(1, ROWS + 1):
            data.set_item(f"rows.r{n}.qty", n)
            data.set_item(f"rows.r{n}.price", 10)
            data.set_item(f"rows.r{n}.total", n * 10)
            data.set_item(f"rows.r{n}.converted", n * 5.0)

    def main(self, root):
        body = root.body()
        body.order_row(iterate="^rows", id="rows_block")
        body.p("after the rows")

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

    def full_render():
        page.render(include_datapath=True)
        return probe.full_html

    # 1. ROW VALUE: one replace of THAT block, oracle-checked.
    with handler.live():
        handler.data.set_item("main.rows.r2.qty", 7)
    patch, = probe.batches[-1]
    assert patch == {"id": "rows_block.r2.1", "op": "replace",
                     "html": patch["html"]}
    assert ">35.0<" in patch["html"]          # 7*10*0.5: the rule chain ran
    assert patch["html"] in full_render()     # ORACLE

    # 2. ROW BORN mid-collection: one insert before the NEXT row's block.
    probe.batches.clear()
    fresh = Bag()
    fresh["qty"] = 1
    fresh["price"] = 10
    fresh["total"] = 10
    fresh["converted"] = 5.0
    with handler.live():
        handler.data.set_item(f"main.rows.r{ROWS + 1}", fresh,
                              node_position="<r3")
    patch, = probe.batches[-1]
    assert patch["op"] == "insert"
    assert patch["before"] == "rows_block.r3.1"
    assert f'id="rows_block.r{ROWS + 1}.1"' in patch["html"]
    assert patch["html"] in full_render()     # ORACLE

    # The new row is LIVE (rules cataloged at its own expansion).
    with handler.live():
        handler.data.set_item(f"main.rows.r{ROWS + 1}.qty", 4)
    assert handler.data[f"main.rows.r{ROWS + 1}.total"] == 40

    # 3. ROW DEAD: one remove by derived id, writeback entries purged.
    probe.batches.clear()
    with handler.live():
        handler.data.pop("main.rows.r2")
    patch, = probe.batches[-1]
    assert patch == {"id": "rows_block.r2.1", "op": "remove"}
    assert not any(k.startswith("rows_block.r2.")
                   for k in page._writeback_map)

    # 4. SHARED-BINDING FLOOD: every row recomputes, the per-row
    # patches coalesce into ONE container replace.
    probe.batches.clear()
    with handler.live():
        handler.data.set_item("main.header.rate", 0.75)
    patch, = probe.batches[-1]
    assert patch["op"] == "replace"
    assert 'id="rows_block' not in patch["id"]    # the container, not a row
    assert patch["html"].count("rows_block.") > ROW_COALESCE_LIMIT

    print("per-row patches OK —", ROWS, "rows,",
          "coalesce limit", ROW_COALESCE_LIMIT)
