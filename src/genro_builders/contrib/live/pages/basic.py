# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Basic demo: a heading and a paragraph bound to data."""

from __future__ import annotations

from ..interactive_demo import InteractiveDemo

DEMO_TITLE = "Basic page"


class Demo(InteractiveDemo):
    """A heading and a paragraph, both bound to data under ``page``."""

    def main(self, root):
        body = root.body(datapath="page", node_id="body")
        body.h1("^.title", node_id="h1")
        body.p("^.message", node_id="msg")

    def seed(self):
        self.set_data("page.title", "Hello")
        self.set_data("page.message", "Scrivi codice Python nella REPL.")
