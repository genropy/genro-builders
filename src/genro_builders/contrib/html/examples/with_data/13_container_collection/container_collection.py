# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""13 — A container collection: the @container citizen. See readme.md.

``DemoContainers`` is the didactic mini collection: ``card`` generates
REAL source nodes at call time (title bar + body) and returns the body
pane the CALLER fills (CMP.9 — fillability is the discriminant between
the two citizens). The effective containers (border/tab) live in a
downstream application layer.
"""
from __future__ import annotations

from genro_builders.contrib.html import DemoContainers, HtmlBuilder


class CustomPage(HtmlBuilder, DemoContainers):
    def main(self, root):
        body = root.body()
        body.h2("Cards")
        row = body.div(display="flex", gap="8px")
        # Each call creates the card's nodes NOW; what comes back is
        # the fillable body — the caller decides what goes inside.
        people = row.card(title="People", flex="1")
        people.p("Anna, Marco, Sara")
        places = row.card(title="Places", flex="1")
        listing = places.ul()
        listing.li("Milano")
        listing.li("Torino")


if __name__ == "__main__":
    page = CustomPage()
    page.create()
    page.set_render_target("output.html")
    page.render(pretty=True)
    print(page.rendered_target)
