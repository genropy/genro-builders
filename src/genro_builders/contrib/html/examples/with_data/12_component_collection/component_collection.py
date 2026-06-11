# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""12 — A component collection: the @component citizen. See readme.md.

``DemoComponents`` is the didactic mini collection: ``labeled_input``
(label + input, the reactive ``value`` pointer passes through to the
inner <input>, CMP.4) and ``swatch`` (a colored box reading a
pointer). The effective widget kit lives in genro-ws-web.
"""
from __future__ import annotations

from genro_builders.builder import BuilderHandler
from genro_builders.contrib.html import DemoComponents, HtmlBuilder


class CustomPage(HtmlBuilder, DemoComponents):
    def setup(self, data):
        data.set_item("person.name", "Mario Rossi")
        data.set_item("person.nickname", "Mario")
        data.set_item("person.color", "#3498db")

    def main(self, root):
        body = root.body(datapath="person")
        body.h2("Profile")
        # The name in the source is the contract (CMP.1); the value
        # pointer reaches the inner <input> with its write-back
        # address (CMP.4).
        body.labeled_input(label="Name", value="^.name")
        # Extra attrs reach the inner input untouched:
        body.labeled_input(label="Nickname", value="^.nickname",
                           placeholder="optional")
        # A closed component reading a pointer in an attribute:
        body.swatch(color="^.color")


if __name__ == "__main__":
    page = CustomPage()
    handler = BuilderHandler()
    handler.add_builder(page)
    page.set_render_target("output.html")
    page.render(pretty=True)
    print(page.rendered_target)
