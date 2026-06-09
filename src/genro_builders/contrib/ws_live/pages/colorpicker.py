# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Color picker page: an input writes data, a box reads it for its border.

Two-way binding end to end. The ``<input type="color">`` is bound with
``value="^.border"``: picking a color writes it back to ``left.style.border``.
The swatch below reads the same datum with ``border_color="^.border"``. So:
pick a color, the box's border follows.

The content lives under the ``left`` branch (the cornice gives the left
pane ``datapath="left"``); a ``style`` div nests below it, so the page data
is at ``left.style.border``.
"""

from __future__ import annotations

from ..base_page import WsLivePage

PAGE_TITLE = "Color picker"


class Page(WsLivePage):
    """An ``<input type="color">`` whose value drives a swatch's border."""

    def setup(self, data):
        self.set_data("left.style.border", "#2c5f8a")

    def main(self, root):
        left_pane = self.cornice(root)
        pane = left_pane.div(datapath=".style")
        pane.h1("Pick a border color")
        pane.input(html_type="color", value="^.border")
        pane.div("Riquadro", class_="swatch", border_color="^.border")
