# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""13 — Containers: border container + tab container. See readme.md.

The @container citizen (CMP.9): real source nodes the caller fills.
The border container is a CSS grid with named areas (sizes live on the
zones, an absent zone collapses by itself); the tab container keeps
the selected key in DATA — the strip click is a mutation, visibility
is pure CSS keyed on the container's data-selected attribute.
"""
from __future__ import annotations

from genro_builders.builder import BuilderHandler
from genro_builders.contrib.html import HtmlBuilder, HtmlContainersBase


class CustomPage(HtmlBuilder, HtmlContainersBase):
    def setup(self, data):
        data.set_item("ui.tab", "people")

    def main(self, root):
        body = root.body()
        bc = body.border_container(height="360px",
                                   border="1px solid #c8c8c8")
        bc.zone("top", height="48px", padding="8px",
                background="#f7f7f7").h2("Containers demo")
        left = bc.zone("left", width="160px", padding="8px",
                       background="#fafafa")
        left.p("A sidebar zone")
        tc = bc.zone("center").tab_container(selected="^ui.tab")
        people = tc.tab("People", key="people")
        people.p("Anna, Marco, Sara")
        places = tc.tab("Places", key="places")
        places.p("Milano, Torino")
        bc.zone("bottom", height="0")          # collapsed, reopenable


if __name__ == "__main__":
    page = CustomPage()
    handler = BuilderHandler()
    handler.add_builder(page)
    page.set_render_target("output.html")
    page.render(pretty=True)
    print(page.rendered_target)
