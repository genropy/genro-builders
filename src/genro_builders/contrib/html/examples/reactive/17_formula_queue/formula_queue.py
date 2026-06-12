# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""17 — Formula queue: formulas queue with dedup, the drain runs at the flush.

Inside a live section a write does not EXECUTE the dependent formulas:
it QUEUES them (FIFO, dedup on the pendings — key ``(spec, row)`` for a
component rule, the node for a page data-element). The drain runs at
the outermost exit, BEFORE the render flush; a drained formula's writes
re-enter the cascade and may re-queue it (a new input arrived during
the drain: dedup is only on the pendings). Controllers never queue — a
command is not a function of the state (two commands are two
executions) and the FIRE payload does not persist.

The case that pays: a page-wide reader (the grand total, binding
``^rows``) on a shared-binding broadcast over N rows used to run once
per EVENT — N executions, each O(N). With the queue the N row rules
drain ahead of it (FIFO = layers) while it stays pending, and it runs
ONCE, on the settled state.

A livelock (formula a -> b -> a) cannot spin: a per-key counter in the
drain raises an explicit error naming the rule.
"""
from __future__ import annotations

from genro_builders.builder import BuilderHandler, TargetWrapper, component
from genro_builders.contrib.html import HtmlBuilder

ROWS = 6


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
    calls = {"grand": 0, "convert": 0}

    @component
    def order_row(self, root, node_label=None):
        row = root.div(datapath="." + node_label)
        row.input(value="^.qty", dtype="L")
        row.span("^.total")
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
        body.data_formula(destination="grand", func="grand_total",
                          rows="^rows", _on_start=True)
        body.span("^grand", id="grand_cell")

    @staticmethod
    def row_total(qty, price):
        if qty is None or price is None:
            return None
        return qty * price

    @staticmethod
    def convert(total, rate):
        CustomPage.calls["convert"] += 1
        if total is None or rate is None:
            return None
        return round(float(total) * float(rate), 2)

    @staticmethod
    def grand_total(rows):
        CustomPage.calls["grand"] += 1
        if rows is None:
            return 0.0
        return round(
            sum(rows[f"{key}.converted"] or 0 for key in rows.keys()), 2,
        )


class LivelockPage(HtmlBuilder):
    def setup(self, data):
        data.set_item("ping", 0)
        data.set_item("pong", 0)

    def main(self, root):
        body = root.body()
        body.data_formula(destination="ping", func="bump", value="^pong")
        body.data_formula(destination="pong", func="bump", value="^ping")
        body.span("^ping")

    @staticmethod
    def bump(value):
        return (value or 0) + 1


if __name__ == "__main__":
    page = CustomPage(name="main")
    probe = Probe()
    page.set_render_target(probe)
    handler = BuilderHandler(application=object())
    handler.add_builder(page)
    handler.activate()

    # _on_start ran the grand once at create (no live section: direct).
    assert CustomPage.calls["grand"] == 1
    assert handler.data["main.grand"] == 105.0      # 5.0 * (1+...+6)

    # 1. BROADCAST: the rate changes, every row reconverts — ONE
    # execution per row (the dedup key is (spec, row): N distinct
    # keys), while the grand stays PENDING behind them (FIFO = layers)
    # and runs ONCE, on the settled state. This used to be N grand
    # executions, each O(N).
    CustomPage.calls.update(grand=0, convert=0)
    with handler.live():
        handler.data.set_item("main.header.rate", 0.75)
    assert CustomPage.calls["convert"] == ROWS
    assert CustomPage.calls["grand"] == 1
    assert handler.data["main.rows.r2.converted"] == 15.0
    assert handler.data["main.grand"] == 157.5      # 7.5 * (1+...+6)

    # 2. CHAINED EDIT: qty -> total -> converted -> grand. The user's
    # own write wakes the wide reader once before the row chain has
    # run; the chain re-queues it once more. Bounded by the dependency
    # depth — never by the number of rows.
    CustomPage.calls.update(grand=0, convert=0)
    with handler.live():
        handler.data.set_item("main.rows.r2.qty", 7)
    assert CustomPage.calls["convert"] == 1         # that row only
    assert CustomPage.calls["grand"] == 2
    assert handler.data["main.rows.r2.total"] == 70
    assert handler.data["main.rows.r2.converted"] == 52.5
    assert handler.data["main.grand"] == 195.0      # 157.5 - 15 + 52.5

    # 3. LIVELOCK BACKSTOP: ping reads pong, pong reads ping, both
    # always write a NEW value — the drain would spin forever. The
    # per-key counter stops it with an error naming the rule.
    lpage = LivelockPage(name="main")
    lprobe = Probe()
    lpage.set_render_target(lprobe)
    lhandler = BuilderHandler(application=object())
    lhandler.add_builder(lpage)
    lhandler.activate()
    try:
        with lhandler.live():
            lhandler.data.set_item("main.ping", 1)
    except RuntimeError as exc:
        assert "bump" in str(exc)
    else:
        raise AssertionError("livelock not detected")

    print("formula queue OK —", ROWS, "rows, grand once per broadcast")
