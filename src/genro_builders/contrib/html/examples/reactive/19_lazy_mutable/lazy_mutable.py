# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""19 — Lazy mutable: store-backed paging, editable rows. See readme.md.

Laziness of the RENDER is orthogonal to the nature of the data. Here
the collection LIVES in the store (no resolver): the iterate says
``lazy=True`` and the first paint ships page 0 plus the marker — but
there is no parking and no transit: a page renders by slicing the LIVE
collection at request time, always current by construction.

Everything editable keeps working, because rules are coordinate
templates on the STORE, not artifacts of rendered blocks (CMP.7): the
row formula of a row that was never painted still fires, the grand
total reads the whole collection from the first calculation. Value
mutations ride the existing per-row/cell lanes (a patch addressed to
an unpainted row is a client no-op). STRUCTURAL mutations are the one
new rule: an insert or delete under a lazy anchor shifts the
placeholder arithmetic, so the flush answers with the REPLACE of the
enclosing container — and a lazy replace costs page 0, not the world.
The client rebuilds placeholders and the viewport refills itself.

Contract: roadmap/reactivity/lazy-iterate.md (v0.4.0).
"""
from __future__ import annotations

from genro_bag import Bag
from genro_builders.builder import BuilderHandler, TargetWrapper, component
from genro_builders.contrib.html import HtmlBuilder

PAGE = 100
TOTAL = 250  # 2 full pages + one of 50


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
        row.span("^.total")
        row.span("^.converted")
        row.dataFormula(destination=".total", func="row_total",
                         qty="^.qty", price="^.price")
        row.dataFormula(destination=".converted", func="convert",
                         total="^.total", rate="^header.rate")

    def setup(self, data):
        # The collection lives in the STORE: no resolver, loaded data
        # is trusted as-is (totals included).
        data.set_item("header.rate", 1.0)
        for i in range(1, TOTAL + 1):
            data.set_item(f"rows.r{i:04d}.qty", 1)
            data.set_item(f"rows.r{i:04d}.price", 2.0)
            data.set_item(f"rows.r{i:04d}.total", 2.0)
            data.set_item(f"rows.r{i:04d}.converted", 2.0)

    def main(self, root):
        body = root.body()
        grid = body.div(id="grid")
        # lazy=True on a store-backed anchor: paging without parking.
        grid.orderRow(iterate="^rows", lazy=True, id="rows_block")
        body.span("^grand.total", id="grand")
        body.dataFormula(destination="grand.total", func="grand_total",
                          rows="^rows", _on_start=True)

    @staticmethod
    def row_total(qty, price):
        if qty is None or price is None:
            return None
        return round(float(qty) * float(price), 2)

    @staticmethod
    def convert(total, rate):
        if total is None or rate is None:
            return None
        return round(float(total) * float(rate), 2)

    @staticmethod
    def grand_total(rows):
        if rows is None:
            return 0
        return round(sum(float(r["total"] or 0) for r in rows.values()), 2)


def simulate_mutate(page, handler, element_id, client_value=None):
    """The server lane, condensed (see 14): resolve by identity, FIRE
    the node's declared path with the hybrid payload."""
    wmap = getattr(page, "_writeback_map", None) or {}
    node = wmap.get(element_id)
    if node is None:
        node = page.node_by_target_id(element_id)
    pointer = node.attr["data-fire-pointer"]
    message = node.attr.get("data-fire-value")
    if message is None:
        message = client_value if client_value is not None else True
    with handler.live():
        node.fire_event(pointer, message)


def block_ids(html, start, stop):
    """Which row-block derived ids of the label range appear in html."""
    return [i for i in range(start, stop)
            if f'id="rows_block.r{i:04d}.1"' in html]


if __name__ == "__main__":
    page = CustomPage(name="main")
    probe = Probe()
    page.set_render_target(probe)
    handler = BuilderHandler(application=object())
    handler.add_builder(page)
    handler.activate()

    html = probe.full_html
    # First paint: page 0 + marker — but the STORE IS FULL (the
    # difference from the read_only catalog of example 18) and the
    # grand total already covers every row, painted or not.
    assert block_ids(html, 1, TOTAL + 1) == list(range(1, PAGE + 1))
    assert '<div id="rows_block.lazy"' in html
    assert f'data-lazy-total="{TOTAL}"' in html
    assert f'data-lazy-page="{PAGE}"' in html
    anchor = handler.data.get_node("main.rows")
    rows_bag = anchor.get_value(static=True)
    assert rows_bag is not None and len(rows_bag) == TOTAL
    assert handler.data["main.grand.total"] == 500.0

    # Page 2 (the partial one) renders from the LIVE collection: no
    # parking, no transit — and the store stays whole afterwards.
    simulate_mutate(page, handler, "rows_block.lazy", client_value=2)
    patch, = probe.batches[-1]
    assert patch["op"] == "page" and patch["page"] == 2
    assert patch["id"] == "rows_block"
    assert block_ids(patch["html"], 1, TOTAL + 1) == list(range(201, 251))
    assert len(anchor.get_value(static=True)) == TOTAL

    # A VALUE edit on a painted row: the existing lanes, untouched —
    # row formula, grand, per-row/cell patches. The lazy container
    # never re-renders for a value.
    with handler.live():
        handler.data.set_item("main.rows.r0001.qty", 5)
    assert handler.data["main.rows.r0001.total"] == 10.0
    assert handler.data["main.grand.total"] == 508.0
    assert all("data-lazy-total" not in str(p.get("html", ""))
               and p.get("op") != "page" for p in probe.batches[-1])

    # A VALUE edit on a row never painted: rules are coordinate
    # templates on the store — the row's formula fires anyway.
    with handler.live():
        handler.data.set_item("main.rows.r0150.qty", 4)
    assert handler.data["main.rows.r0150.total"] == 8.0
    assert handler.data["main.grand.total"] == 514.0

    # STRUCTURAL: a new row shifts the placeholder arithmetic — the
    # flush answers with the CONTAINER replace (page 0 + fresh marker
    # count), never a row insert.
    row = Bag()
    row["qty"] = 1
    row["price"] = 2.0
    row["total"] = 2.0
    with handler.live():
        handler.data.set_item("main.rows.r0251", row)
    batch = probe.batches[-1]
    rep = next(p for p in batch
               if "data-lazy-total" in str(p.get("html", "")))
    assert rep["op"] == "replace"
    assert f'data-lazy-total="{TOTAL + 1}"' in rep["html"]
    assert 'id="rows_block.r0001.1"' in rep["html"]
    assert 'id="rows_block.r0150.1"' not in rep["html"]
    assert not any(p.get("op") in ("insert", "page") for p in batch)
    assert handler.data["main.grand.total"] == 516.0

    # Same rule for the delete.
    with handler.live():
        handler.data.pop("main.rows.r0251")
    batch = probe.batches[-1]
    rep = next(p for p in batch
               if "data-lazy-total" in str(p.get("html", "")))
    assert f'data-lazy-total="{TOTAL}"' in rep["html"]
    assert not any(p.get("op") == "remove" for p in batch)
    assert handler.data["main.grand.total"] == 514.0

    # BROADCAST economics: the rate touches EVERY row's converted.
    # The STORE updates for all of them (rules are coordinate
    # templates), but the wire carries value patches ONLY for the rows
    # the client HAS — after the structural replaces, page 0 again.
    # Without the delivered filter this would ship TOTAL patches and
    # the client would drop all but PAGE of them.
    with handler.live():
        handler.data.set_item("main.header.rate", 2.0)
    assert handler.data["main.rows.r0001.converted"] == 20.0
    assert handler.data["main.rows.r0150.converted"] == 16.0  # unpainted
    batch = probe.batches[-1]
    value_ops = [p for p in batch if p.get("op") in ("text", "attr")]
    delivered = {f"rows_block.r{i:04d}" for i in range(1, PAGE + 1)}
    assert len(value_ops) == PAGE, f"{len(value_ops)} ops on the wire"
    assert all(p["id"].rsplit(".", 1)[0] in delivered for p in value_ops)

    print("store-backed lazy:", TOTAL, "rows — grand:",
          handler.data["main.grand.total"])
