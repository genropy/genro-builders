# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""18 — Lazy iterate: virtual scroll, the server side. See readme.md.

A big IMMUTABLE collection (a catalog) must not make the first paint
pay for every row: the anchor holds a ``read_only`` resolver (the
query, declared on the DATA) and the iterate says ``lazy=True``. At
first render the query runs ONCE: the rows go to the handler's parking
dict, paginated; the walk expands ONLY page 0 inline, plus a MARKER
carrying the total count and the FIRE lane for the rest. The store
never holds the collection.

The client (simulated here) fabricates placeholders for the missing
rows and asks pages as the user scrolls — each request is its own
transaction: fire the marker with the page number, get one ``page`` op
back with the rendered blocks. A page TRANSITS the store silently
(``set_item`` with ``resolver=False, do_trigger=False``, render,
restore): no events, no spurious row_ins, nothing persisted. Delivered
rows stay alive as fire targets (selection by baked label: the wmap
retains expansion nodes, not the store).

Contract: roadmap/reactivity/lazy-iterate.md (v0.3.0).
"""
from __future__ import annotations

from genro_bag import Bag
from genro_bag.resolver import BagCbResolver
from genro_builders.builder import BuilderHandler, TargetWrapper, component
from genro_builders.contrib.html import HtmlBuilder

PAGE = 100
TOTAL = 350  # 3 full pages + one of 50


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
    def catalogRow(self, root, node_label=None):
        row = root.div(datapath="." + node_label)
        row.span("^.name")
        row.span("^.price")
        row.button("pick", **{"data-fire-pointer": "selection",
                              "data-fire-value": node_label})

    def setup(self, data):
        # ALL the author writes for lazy: the query on the anchor...
        data.set_item(
            "catalog", BagCbResolver(self.load_catalog, read_only=True),
        )

    def main(self, root):
        body = root.body()
        # ...and lazy=True on the iterate. Nothing else.
        body.catalogRow(iterate="^catalog", lazy=True, id="catalog_block")
        body.input(value="^note")
        body.dataController(func="on_pick", picked="^selection")

    @staticmethod
    def load_catalog():
        """The query, run ONCE at first render: TOTAL immutable rows."""
        rows = Bag()
        for i in range(TOTAL):
            rows[f"p{i:04d}.name"] = f"product {i}"
            rows[f"p{i:04d}.price"] = i * 10
        return rows

    @staticmethod
    def on_pick(node, picked=None):
        if picked:
            node.SET("chosen", picked)


def simulate_mutate(page, handler, element_id, client_value=None):
    """The server lane, condensed (see 14): resolve by identity, FIRE
    the node's declared path with the hybrid payload (node wins ->
    client -> True). A page request is the marker fired with the page
    number as the client's value.
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


def block_ids(html, start, stop):
    """Which row-block derived ids (ordinal 1 = the block root) of the
    label range [start, stop) appear in ``html``."""
    return [i for i in range(start, stop)
            if f'id="catalog_block.p{i:04d}.1"' in html]


if __name__ == "__main__":
    page = CustomPage(name="main")
    probe = Probe()
    page.set_render_target(probe)
    handler = BuilderHandler(application=object())
    handler.add_builder(page)
    handler.activate()

    html = probe.full_html
    # First paint: page 0 INLINE — exactly the first PAGE blocks, not
    # all TOTAL. The author's id is the base of the derived chain.
    assert block_ids(html, 0, TOTAL) == list(range(PAGE))
    # The marker: identity, the lane for the rest, the baked counts.
    # It wears the row blocks' own root tag (a div among the divs:
    # DOM validity wherever the rows live — tr, li, option...).
    assert '<div id="catalog_block.lazy"' in html
    assert 'data-fire-pointer="_lazy.catalog_block"' in html
    assert f'data-lazy-total="{TOTAL}"' in html
    assert f'data-lazy-page="{PAGE}"' in html
    # The store never holds the collection: the read_only resolver is
    # in place, nothing was deposited on the anchor.
    anchor = handler.data.get_node("main.catalog")
    assert anchor.get_value(static=True) is None

    # Grab the scrollbar: page 3 (the partial one, 50 rows) WITHOUT
    # ever asking pages 1 and 2.
    simulate_mutate(page, handler, "catalog_block.lazy", client_value=3)
    patch, = probe.batches[-1]
    assert patch["op"] == "page"
    assert patch["id"] == "catalog_block"
    assert patch["page"] == 3
    assert block_ids(patch["html"], 0, TOTAL) == list(range(300, TOTAL))
    assert "product 349" in patch["html"] and "3490" in patch["html"]
    # Transit, not deposit: the store is clean after delivery.
    assert anchor.get_value(static=True) is None

    # Life in between: an ordinary edit between two page requests goes
    # through its own transaction, untouched by the lazy machinery.
    with handler.live():
        handler.data.set_item("main.note", "hello")
    assert probe.batches[-1]
    assert all(p.get("op") != "page" for p in probe.batches[-1])

    simulate_mutate(page, handler, "catalog_block.lazy", client_value=1)
    patch, = probe.batches[-1]
    assert patch["page"] == 1
    assert block_ids(patch["html"], 0, TOTAL) == list(range(100, 200))

    # Selection on a DELIVERED row: the button is a live fire target,
    # its label baked at expansion — identity survives the transit.
    simulate_mutate(page, handler, "catalog_block.p0301.4")
    assert handler.data["main.chosen"] == "p0301"

    print("first paint:", PAGE, "of", TOTAL,
          "— chosen:", handler.data["main.chosen"])
