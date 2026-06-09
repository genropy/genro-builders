# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Basic page: a heading and a paragraph bound to data under ``left.page``.

The content lives under the ``left`` branch (the cornice gives the left
pane ``datapath="left"``); a ``page`` div nests below it, so the page data
is at ``left.page.title`` / ``left.page.message``.
"""

from __future__ import annotations

from ..base_page import WsLivePage

PAGE_TITLE = "Basic page"


class Page(WsLivePage):
    """A heading and a paragraph, both bound to data under ``left.page``."""

    def setup(self, data):
        self.set_data("left.page.title", "Hello")
        self.set_data("left.page.message", "Scrivi codice Python nella REPL.")

    def main(self, root):
        left_pane = self.cornice(root)
        pane = left_pane.div(datapath=".page", node_id="page")
        pane.h1("^.title", node_id="h1")
        pane.p("^.message")
