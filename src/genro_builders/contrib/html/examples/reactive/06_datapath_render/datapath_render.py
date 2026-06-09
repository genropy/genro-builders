# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""06 — Datapath render: the markup carries the hooks a client patches.

Rendering with ``include_datapath=True`` (the reactive render mode) adds,
on every pointer-bound node, a stable ``id`` (its path inside the document,
e.g. ``body.h1_0``) and, for each pointer-bound attribute, a
``data-<name>-pointer`` carrying the absolute datapath. Those are the hooks
the client side uses: the ``id`` is the target of a "node <id> changed"
patch, the ``data-*-pointer`` is the write-back path for an input event.
"""
from __future__ import annotations

from genro_builders.builder import BuilderHandler
from genro_builders.contrib.html import HtmlBuilder


class CustomPage(HtmlBuilder):
    def setup(self, data):
        data.set_item("message", "Hello Folk")

    def main(self, root):
        body = root.body()
        body.h1("^message")
        body.input(value="^message", placeholder="edit me")


if __name__ == "__main__":
    page = CustomPage()
    handler = BuilderHandler()
    handler.add_builder(main=page)
    page.set_render_target("output.html")
    page.render(include_datapath=True)
    print(page.rendered_target)
