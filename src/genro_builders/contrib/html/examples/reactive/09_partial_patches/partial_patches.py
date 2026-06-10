# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""09 — Partial patches: the destination decides the delivery. See readme.md.

Instead of a raw target the page registers a TargetWrapper: a
destination object. This one accepts partial delivery, so the live()
flush sends per-node patches (id = the node's DOM id, op = replace,
html = the re-rendered node) instead of re-rendering the page.
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
        data.set_item("name", "John")
        data.set_item("css", "color: red")

    def main(self, root):
        body = root.body()
        body.h1("Patch demo")
        body.div("^name", style="^css")


if __name__ == "__main__":
    wrapper = PatchLog("output.html", "patches.json")
    page = CustomPage(name="main")
    page.set_render_target(wrapper)
    handler = BuilderHandler(application=object())
    handler.add_builder(page)
    handler.activate()                  # full render -> output.html

    with handler.live():
        handler.data.set_item("main.name", "Martin")

    with handler.live():
        handler.data.set_item("main.css", "color: blue")
        handler.data.set_item("main.name", "Martin Blue")

    print(Path("output.html").read_text())
    print(json.dumps(wrapper.batches, indent=2))
