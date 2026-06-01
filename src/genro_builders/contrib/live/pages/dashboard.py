# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Dashboard demo: header, nav, panels and buttons — a richer layout."""

from __future__ import annotations

from ..interactive_demo import InteractiveDemo

DEMO_TITLE = "Dashboard"


class Demo(InteractiveDemo):
    """A header bar, a nav, and two stat panels with action buttons.

    Data lives under ``ui``: ``ui.title``, ``ui.users``, ``ui.revenue``.

    Naming a node is opt-in, and the two ways differ in purpose. Here the
    structural nodes carry a ``node_label`` — a readable key in the source
    bag — so a panel can be reached by *path* via subscript, at any depth:

        source["body.panels.users"]

    Each path segment may also be positional — ``#n`` selects the n-th child
    — and the two forms mix freely in one path (``#0.panels.users``). (A
    ``node_id``, by contrast, is an absolute anchor: ``node_by_id("x")``,
    used by the REPL — see ``basic``.) Neither label nor id shows up in the
    rendered HTML, and the page renders fine without either; they exist only
    for code that wants to find the node again. Nodes never looked up — the
    nav buttons, the footer — stay anonymous.
    """

    def setup(self):
        self.set_data("ui.title", "Dashboard")
        self.set_data("ui.users", "1 248 active")
        self.set_data("ui.revenue", "€ 84,500")

    def main(self, root):
        body = root.body(datapath="ui", node_label="body")
        body.link(rel="stylesheet", href="demo_css")

        header = body.header(_class="bar")
        header.h1("^.title")
        nav = header.nav()
        nav.button("Overview", html_type="button")
        nav.button("Reports", html_type="button")
        nav.button("Settings", html_type="button")

        panels = body.main(node_label="panels", _class="panels")

        users = panels.section(node_label="users", _class="panel")
        users.h2("Users")
        users.p("^.users")
        users.button("Refresh", html_type="button")

        revenue = panels.section(node_label="revenue", _class="panel")
        revenue.h2("Revenue")
        revenue.p("^.revenue")
        revenue.button("Export", html_type="button")

        footer = body.footer()
        footer.span("genro-builders live demo")
