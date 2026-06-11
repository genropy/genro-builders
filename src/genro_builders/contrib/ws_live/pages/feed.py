# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Feed page: structural patches pushed by the server.

Every second ``tick()`` ATTACHES a new line to the source — it reaches
the browser as an ``insert`` patch (the new fragment only, the sibling
elements never travel). Past five lines the oldest is dropped: a
``remove`` patch, just the id. The list grows and scrolls with no
client request and no replace of the container.
"""

from __future__ import annotations

from datetime import datetime

from ..base_page import WsLivePage

PAGE_TITLE = "Feed (structural push)"


class Page(WsLivePage):
    """A server-pushed feed: lines enter as inserts, leave as removes."""

    live_interval = 1.0

    def setup(self, data):
        self._counter = 0

    def main(self, root):
        pane = root.div()
        pane.h1("Server feed")
        pane.ul(node_id="feed", class_="feed")
        pane.p(
            "One insert per second, capped at five lines: the oldest "
            "leaves with a remove. No replace, no client request.",
        )

    def tick(self):
        self._counter += 1
        stamp = datetime.now().strftime("%H:%M:%S")
        feed = self.node_by_id("feed")
        feed.li(f"event #{self._counter} — {stamp}")
        items = list(feed.value)
        if len(items) > 5:
            feed.value.pop(items[0].label)
