# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""12 — Writeback identity: the virtual-children map. See readme.md.

Expansion nodes never get a serial of their own (they reincarnate);
in the reactive render their identity is DERIVED and deterministic:
``<base>.<iteration label>....<ordinal>``. The WRITABLE nodes (a
pointer on ``value``/``checked``) land in ``builder._writeback_map``:
a mutation arrives as ``{id, value}`` and the server reads EVERYTHING
from the resolved node — the dtype (typing), the ``validate_*``
family (retained on the node, never emitted in HTML), the destination
(the pointer, absolutized). No path and no dtype travel on the wire.
"""
from __future__ import annotations

import json
from pathlib import Path

from genro_builders.builder import BuilderHandler, TargetWrapper, component
from genro_builders.contrib.html import HtmlBuilder
from genro_tytx.utils import raw_decode


class PatchLog(TargetWrapper):
    """Writes the full document to a file; logs every patch batch."""

    accepts_partial = True
    render_opts = {"include_datapath": True}

    def __init__(self, document_path, patches_path):
        self.document_path = Path(document_path)
        self.patches_path = Path(patches_path)
        self.batches: list[list[dict]] = []

    def full(self, document):
        self.document_path.write_text(document, encoding="utf-8")

    def partial(self, patches):
        self.batches.append(patches)
        self.patches_path.write_text(
            json.dumps(self.batches, indent=2), encoding="utf-8",
        )


class CustomPage(HtmlBuilder):
    @component
    def state_row(self, root, node_label=None):
        row = root.tr(datapath="." + node_label)
        row.td("^.name")                       # pure reader: NOT in the map
        cell = row.td()
        cell.input(value="^.name", dtype="A", validate_len="3:")
        cell.input(value="^.population", dtype="L")

    def setup(self, data):
        data.set_item("states.NSW.name", "New South Wales")
        data.set_item("states.NSW.population", 8166000)
        data.set_item("states.VIC.name", "Victoria")
        data.set_item("states.VIC.population", 6681000)

    def main(self, root):
        body = root.body()
        body.table().tbody().state_row(iterate="^states")


def mutate_by_id(page, handler, composite_id, raw_value):
    """What the application's mutate does: id in, node says the rest."""
    node = page._writeback_map[composite_id]
    dtype = node.attr.get("dtype")
    value = raw_value
    if dtype and dtype not in ("A", "T"):      # text stays text
        decoded, typed = raw_decode(f"{raw_value}::{dtype}")
        if not decoded:
            raise ValueError(f"unknown dtype {dtype!r}")
        value = typed
    path = node.abs_datapath(node.attr["value"])
    with handler.live():
        handler.data.set_item(path, value)
    return value


if __name__ == "__main__":
    wrapper = PatchLog("output.html", "patches.json")
    page = CustomPage(name="main")
    page.set_render_target(wrapper)
    handler = BuilderHandler(application=object())
    handler.add_builder(page)
    handler.activate()

    document = wrapper.document_path.read_text(encoding="utf-8")
    # Derived ids on the DOM, one chain per row; retention keeps the
    # validate_* family OFF the markup.
    assert 'id="n1.VIC.4"' in document and 'id="n1.NSW.4"' in document
    assert "validate_len" not in document
    # Only the writable nodes are in the map (2 inputs x 2 rows).
    assert sorted(page._writeback_map) == [
        "n1.NSW.4", "n1.NSW.5", "n1.VIC.4", "n1.VIC.5",
    ]

    # A mutation addressed by id: typed by the NODE's dtype, landed at
    # the NODE's pointer — only Victoria's population changes.
    value = mutate_by_id(page, handler, "n1.VIC.5", "6700000")
    assert value == 6700000 and isinstance(value, int)
    assert handler.data["main.states.VIC.population"] == 6700000
    assert handler.data["main.states.NSW.population"] == 8166000

    print("writeback map:", sorted(page._writeback_map))
    print("VIC population:", handler.data["main.states.VIC.population"])
