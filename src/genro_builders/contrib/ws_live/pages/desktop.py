# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Desktop page: border + tab containers hosting live pages in iframes.

The shell preview: a border container (header on top, a sidebar on the
left) with a tab container in the center whose panes host OTHER ws_live
pages in iframes. The selected key lives in data; the strip click is a
mutation; switching is an attribute-only morph — the iframes are never
touched, so a background page keeps living (the clock keeps ticking)
and switching back finds it exactly where it was.
"""

from __future__ import annotations

from genro_builders.contrib.html import HtmlContainersBase

from ..base_page import WsLivePage

PAGE_TITLE = "Desktop (containers + iframes)"


class Page(WsLivePage, HtmlContainersBase):
    """A miniature desktop: tabs are live pages, switching reloads nothing."""

    def setup(self, data):
        self.set_data("ui.tab", "widgets")

    def main(self, root):
        bc = root.border_container(height="calc(100vh - 48px)")
        bc.zone("top", height="48px", padding="8px",
                background="#f0f4f8").h2("Desktop", margin="0")
        side = bc.zone("left", width="180px", padding="8px",
                       background="#fafafa")
        side.p("Every tab is a live page; switching tabs reloads nothing.")
        tc = bc.zone("center").tab_container(selected="^ui.tab")
        tc.tab("Widgets", key="widgets").iframe(
            src="widgets", width="100%", height="500px", border="none",
        )
        tc.tab("Clock", key="clock").iframe(
            src="clock", width="100%", height="500px", border="none",
        )
        feed = tc.tab("Feed", key="feed")
        feed.iframe(src="feed", width="100%", height="500px", border="none")
