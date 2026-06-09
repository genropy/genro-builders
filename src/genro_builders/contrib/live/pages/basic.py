# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Basic demo: a heading and a paragraph bound to data."""

from __future__ import annotations

from ..interactive_demo import InteractiveDemo

DEMO_TITLE = "Basic page"


class Demo(InteractiveDemo):
    """A heading and a paragraph, both bound to data under ``page``.

    Only ``body`` and ``h1`` carry a ``node_id``: those are the nodes the
    REPL reaches by name (``page.node_by_id("h1").set_attr(...)``). A
    ``node_id`` is an explicit anchor — give one *only* when something will
    look the node up later. The paragraph needs none, so it has none.
    """

    def setup(self, data):
        self.set_data("page.title", "Hello")
        self.set_data("page.message", "Scrivi codice Python nella REPL.")

    def main(self, root):
        body = root.body(datapath="page", node_id="body")
        body.link(rel="stylesheet", href="demo_css")
        body.h1("^.title", node_id="h1")
        body.p("^.message")
