# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Basic page: a heading and a paragraph bound to data under ``page``."""

from __future__ import annotations

from ..base_page import WsLivePage

PAGE_TITLE = "Basic page"


class Page(WsLivePage):
    """A heading and a paragraph, both bound to data under ``page``."""

    def setup(self, data):
        self.set_data("page.title", "Hello")
        self.set_data("page.message", "Scrivi codice Python nella REPL.")

    def main(self, root):
        pane = root.div(datapath="page", node_id="page")
        pane.h1("^.title", node_id="h1")
        pane.p("^.message")
