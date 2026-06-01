# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Color picker demo: an input writes data, a box reads it for its border.

Two-way binding end to end. The ``<input type="color">`` is bound with
``value="^.border"``: picking a color writes it back to ``style.border``
(the browser reads ``data-value-pointer`` and calls the ``set_value``
route). The swatch below reads the same datum with ``border_color="^.border"``
— a pull pointer feeding a Genro-style CSS attribute. So: pick a color,
the box's border follows. The base border width/style are fixed in
``demo.css`` (``.swatch``); only the color is data-driven.
"""

from __future__ import annotations

from ..interactive_demo import InteractiveDemo

DEMO_TITLE = "Color picker"


class Demo(InteractiveDemo):
    """An ``<input type="color">`` whose value drives a swatch's border.

    Data lives under ``style.border``. The input writes it on change; the
    swatch reads it as ``border-color``.
    """

    def setup(self):
        self.set_data("style.border", "#2c5f8a")

    def main(self, root):
        body = root.body(datapath="style")
        body.link(rel="stylesheet", href="demo_css")
        body.h1("Pick a border color")
        body.input(html_type="color", value="^.border")
        body.div("Riquadro", _class="swatch", border_color="^.border")


if __name__ == "__main__":
    demo = Demo()
    demo.create()
    print(demo.render())
