# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Clock page: server-initiated reactivity, no client request involved.

The page declares ``live_interval``: the app runs ``tick()`` inside a
``live()`` section every second. The mutation re-renders the readers
and the patches are PUSHED over the websocket — the browser clock
ticks without ever asking.
"""

from __future__ import annotations

from datetime import datetime

from ..base_page import WsLivePage

PAGE_TITLE = "Clock (server push)"


class Page(WsLivePage):
    """A clock the SERVER keeps alive: the browser never asks."""

    live_interval = 1.0

    def setup(self, data):
        self.set_data("clock.now", datetime.now().strftime("%H:%M:%S"))

    def main(self, root):
        pane = root.div(datapath="clock")
        pane.h1("Server clock")
        pane.div("^.now", class_="clock")
        pane.p("Pushed every second by the server: no client request.")

    def tick(self):
        self.set_data("clock.now", datetime.now().strftime("%H:%M:%S"))
