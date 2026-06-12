# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""16 — Attribute-mode rows: row = ONE node, columns = node ATTRIBUTES.

See readme.md. Legacy parity: the grid rides values or attributes; in
attribute mode the store is flat (N nodes instead of N x columns) and
a whole row arrives as ONE ins event with its columns aboard. The bag
speaks the dialect natively (``set_item("rows.r1?qty", 2)``; attribute
changes trigger ``upd_attrs`` on the node path); the builders side:

1. pointers to own-row attributes resolve: ``^.?qty`` from the row
   anchor (abs_datapath keeps the ``?attr`` tail);
2. the reactive render shows attribute values and emits the write-back
   hook with the ``?attr`` path;
3. the mutate lane writes back: derived id -> node -> abs path with
   ``?attr`` -> set_item -> upd_attrs -> per-row patch (row_upd);
4. row logic binds attributes: a rule with ``qty="^.?qty"`` triggers
   on the attr change (the ``?attr`` tail strips in the matching,
   like the pointer_map) and writes its destination attr.
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
    def attr_row(self, root, node_label=None):
        row = root.div(datapath="." + node_label)
        row.span("^.")                       # the node VALUE (description)
        row.input(value="^.?qty", dtype="L")
        row.span("^.?total")
        row.data_formula(destination=".?total", func="row_total",
                         qty="^.?qty", price="^.?price")

    def setup(self, data):
        for label, descr, qty, price in (
            ("r1", "Keyboard", 2, 10), ("r2", "Monitor", 3, 5),
        ):
            data.set_item(f"rows.{label}", descr)
            data.set_item(f"rows.{label}?qty", qty)
            data.set_item(f"rows.{label}?price", price)
            data.set_item(f"rows.{label}?total", qty * price)

    def main(self, root):
        root.body().attr_row(iterate="^rows", id="rows_block")

    @staticmethod
    def row_total(qty, price):
        if qty is None or price is None:
            return None
        return qty * price


if __name__ == "__main__":
    page = CustomPage(name="main")
    probe = Probe()
    page.set_render_target(probe)
    handler = BuilderHandler(application=object())
    handler.add_builder(page)
    handler.activate()

    # 1+2. the render reads values AND attributes; loaded data trusted.
    html = probe.full_html
    assert "Keyboard" in html and "Monitor" in html
    assert 'value="2"' in html, html
    assert ">20<" in html                  # r1 total attr, shown
    print("render OK")

    # the write-back hook carries the ?attr path
    assert 'data-value-pointer="main.rows.r1?qty"' in html, html

    # 3. the mutate lane: resolve the qty input by derived id, write.
    wmap = page._writeback_map
    qty_id = next(k for k, n in wmap.items()
                  if ".r1." in k
                  and n.attr.get("value", "").endswith("?qty"))
    node = wmap[qty_id]
    abs_path = node.abs_datapath(node.attr["value"])
    assert abs_path == "main.rows.r1?qty", abs_path
    probe.batches.clear()
    with handler.live():
        handler.data.set_item(abs_path, 7)

    # 4. the row rule ran on the ATTR binding and wrote its attr.
    assert handler.data.get_item("main.rows.r1?total") == 70
    # ...and the flush patched ONE row (attr change -> upd_attrs ->
    # row_upd by path arithmetic).
    flat = [p for batch in probe.batches for p in batch]
    assert all(p["id"].startswith("rows_block.r1") for p in flat), flat
    replaces = [p for p in flat if p["op"] == "replace"]
    assert any(">70<" in p["html"] for p in replaces), flat
    # the sibling row r2 never travelled
    assert all(".r2." not in p.get("html", "") for p in flat)

    print("attr grid OK — one-row patches:", len(flat),
          "| store nodes per row: 1")
