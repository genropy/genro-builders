# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""14 — Page command: the FIRE lane of the wire (+/− rows). See readme.md.

A click that must RUN LOGIC (not write a datum) is still a mutation
``{id, value}``: the element declares the fired path
(``data-fire-pointer``) and optionally the message
(``data-fire-value``); the server resolves the node by identity and
FIREs the path — the datastore is the message bus (path = topic,
fired value = payload, never persisted). A ``data_controller`` bound
to the path is the subscriber: it performs the STRUCTURAL store op
(add/remove a row) and the iterate block re-renders.

Hybrid payload rule: a node-declared ``data-fire-value`` wins (the
per-row "−" bakes the row label at expansion: the click is pure
identity); no declaration -> the client's value IS the message;
none -> ``True`` (the footer "+").

Deletion kills the rules ANCHORED in the deleted subtree: a dead
row's rule never runs again (its destination write would autocreate
the row back) — while rules merely reading under the deleted path
keep recomputing.
"""
from __future__ import annotations

from genro_bag import Bag
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
    def order_row(self, root, node_label=None):
        row = root.div(datapath="." + node_label)
        row.input(value="^.qty", dtype="L")
        row.span("^.converted")
        # The per-row command: the message (WHICH row) is the node's
        # own attribute, baked at expansion — the click is identity.
        row.button("−", **{"data-fire-pointer": "commands.del_row",
                           "data-fire-value": node_label})
        row.data_formula(destination=".total", func="row_total",
                         qty="^.qty", price="^.price")
        row.data_formula(destination=".converted", func="convert",
                         total="^.total", rate="^header.rate")

    def setup(self, data):
        data.set_item("header.rate", 0.5)
        for label, qty, price in (("r1", 2, 10), ("r2", 3, 5)):
            data.set_item(f"rows.{label}.qty", qty)
            data.set_item(f"rows.{label}.price", price)
            data.set_item(f"rows.{label}.total", qty * price)
            data.set_item(f"rows.{label}.converted", qty * price * 0.5)

    def main(self, root):
        body = root.body()
        body.order_row(iterate="^rows", id="rows_block")
        # The page command, footer side: no declared message — the
        # fired value defaults to True. NB: no author id — a clicked
        # source node rides its SERIAL (the author's id is not
        # mutation addressable).
        body.button("+", **{"data-fire-pointer": "commands.add_row"})
        body.data_controller(func="add_row", trigger="^commands.add_row")
        body.data_controller(func="del_row", label="^commands.del_row")
        body.data_formula(destination="grand.total", func="grand_total",
                          rows="^rows", _on_start=True)

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

    @staticmethod
    def grand_total(rows):
        if rows is None:
            return 0
        return sum(r["total"] or 0 for r in rows.values())

    @staticmethod
    def add_row(node, trigger=None):
        if not trigger:
            return
        rows = node.GET("rows")
        ordinal = 1 + max(
            (int(lbl[1:]) for lbl in rows.keys() if lbl[1:].isdigit()),
            default=0,
        )
        row = Bag()
        row["qty"] = 1
        row["price"] = 0
        row["total"] = 0
        row["converted"] = 0
        node.SET(f"rows.r{ordinal}", row)

    @staticmethod
    def del_row(node, label=None):
        if not label:
            return
        node.data_handler.data.pop(node.abs_datapath(f"rows.{label}"))


def simulate_mutate(page, handler, element_id, client_value=None):
    """The server lane, condensed: resolve by identity, FIRE the node's
    declared path with the hybrid payload (node wins -> client -> True).
    """
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


if __name__ == "__main__":
    page = CustomPage(name="main")
    probe = Probe()
    page.set_render_target(probe)
    handler = BuilderHandler(application=object())
    handler.add_builder(page)
    handler.activate()

    # The per-row "−" buttons carry DERIVED ids and sit in the
    # writeback map: click targets are mutation targets.
    wmap = page._writeback_map
    fire_ids = sorted(k for k, n in wmap.items()
                      if n.attr.get("data-fire-pointer"))
    assert fire_ids == ["rows_block.r1.4", "rows_block.r2.4"]
    assert handler.data["main.grand.total"] == 35

    # DEL: fire the r2 button -> the controller pops the row -> the
    # iterate block re-renders without it, the grand total follows.
    simulate_mutate(page, handler, "rows_block.r2.4")
    assert handler.data.get_item("main.rows.r2") is None
    assert list(handler.data["main.rows"].keys()) == ["r1"]
    assert handler.data["main.grand.total"] == 20
    # The patch is SURGICAL (per-row, CMP.7): one remove addressed by
    # the row block's derived identity — never the whole container.
    assert probe.batches[-1] == [
        {"id": "rows_block.r2.1", "op": "remove"},
    ]

    # The dead row's rules died with it: a SHARED binding (the rate)
    # recomputes the survivors and never resurrects r2.
    with handler.live():
        handler.data.set_item("main.header.rate", 0.75)
    assert handler.data.get_item("main.rows.r2") is None
    assert handler.data["main.rows.r1.converted"] == 15.0

    # ADD: the footer "+" declares no value -> message defaults True.
    # The button is a SOURCE node: the wire carries its serial.
    queue = [page.source]
    add_serial = None
    while queue:
        for n in queue.pop(0).nodes:
            if n.attr.get("data-fire-pointer") == "commands.add_row":
                add_serial = n._target_id
            if hasattr(n.value, "nodes"):
                queue.append(n.value)
    assert add_serial, "the + button must carry a serial"
    probe.batches.clear()
    simulate_mutate(page, handler, add_serial)
    assert list(handler.data["main.rows"].keys()) == ["r1", "r2"]
    assert handler.data["main.rows.r2.qty"] == 1
    # Surgical again: ONE insert of the new block, anchored before the
    # element that follows the rows (the + button itself).
    patch, = probe.batches[-1]
    assert patch["op"] == "insert"
    assert patch["before"] == add_serial
    assert 'id="rows_block.r2.1"' in patch["html"]

    # The new row is LIVE: its rules were cataloged at re-expansion.
    with handler.live():
        handler.data.set_item("main.rows.r2.price", 8)
    with handler.live():
        handler.data.set_item("main.rows.r2.qty", 4)
    assert handler.data["main.rows.r2.total"] == 32
    assert handler.data["main.rows.r2.converted"] == 24.0
    assert handler.data["main.grand.total"] == 52

    # FIRE is an event, not a datum: nothing persists on the topic.
    assert handler.data.get_item("main.commands.del_row") is None
    assert handler.data.get_item("main.commands.add_row") is None
    print("rows:", list(handler.data["main.rows"].keys()),
          "grand:", handler.data["main.grand.total"])
