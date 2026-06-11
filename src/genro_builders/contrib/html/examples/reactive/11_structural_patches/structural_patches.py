# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""11 — Structural patches: insert and remove ride the envelope. See readme.md.

The source tree changes shape at runtime: a node attached inside a
live() section travels as an ``insert`` patch (the new fragment only,
anchored by ``before``), a dropped node as a ``remove`` (its id is all
the client needs). The sibling elements are never touched — which is
the whole point: an <iframe> sitting next to the mutation would NOT
reload.
"""
from __future__ import annotations

import json
from pathlib import Path

from genro_builders.builder import BuilderHandler, TargetWrapper
from genro_builders.contrib.html import HtmlBuilder


class PatchLog(TargetWrapper):
    """Writes the full document to a file; logs every patch batch."""

    accepts_partial = True
    render_opts = {"include_datapath": True}   # patches need DOM ids

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
    def setup(self, data):
        data.set_item("title", "Groceries")

    def main(self, root):
        body = root.body()
        body.h1("^title")
        todo = body.ul(node_id="list")
        todo.li("bread")
        todo.li("milk")


if __name__ == "__main__":
    wrapper = PatchLog("output.html", "patches.json")
    page = CustomPage(name="main")
    page.set_render_target(wrapper)
    handler = BuilderHandler(application=object())
    handler.add_builder(page)
    handler.activate()                  # full render -> output.html

    todo = page.node_by_id("list")

    with handler.live():
        # A node attached to the source: ONE insert patch, appended
        # (`before` is null), the existing items never travel.
        todo.li("apples")

    with handler.live():
        # node_position picks the spot; the patch expresses it as the
        # target_id of the following sibling (`before`).
        todo.li("coffee — urgent", node_position="<")

    with handler.live():
        # A node dropped from the source: a remove patch, id only (the
        # id was captured at the delete event — the node is already
        # gone by flush time).
        todo.value.pop("li_1")          # milk

    with handler.live():
        # Born and died in the same section: the DOM never saw it, the
        # optimizer nets ins+del to nothing — the batch is empty.
        ghost = todo.li("ghost")
        todo.value.pop(ghost.label)

    print(Path("output.html").read_text())
    print(json.dumps(wrapper.batches, indent=2))
