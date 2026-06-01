# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Dashboard demo: header, nav, panels and buttons — a richer layout."""

from __future__ import annotations

from ..interactive_demo import InteractiveDemo

DEMO_TITLE = "Dashboard"


class Demo(InteractiveDemo):
    """A header bar, a nav, and two stat panels with action buttons.

    Data lives under ``ui``: ``ui.title``, ``ui.users``, ``ui.revenue``.
    """

    def setup(self):
        self.set_data("ui.title", "Dashboard")
        self.set_data("ui.users", "1 248 active")
        self.set_data("ui.revenue", "€ 84,500")

    def main(self, root):
        body = root.body(datapath="ui", node_id="body")
        body.link(rel="stylesheet", href="demo_css")

        header = body.header(node_id="hdr", _class="bar")
        header.h1("^.title", node_id="title")
        nav = header.nav(node_id="nav")
        nav.button("Overview", node_id="nav_overview", _type="button")
        nav.button("Reports", node_id="nav_reports", _type="button")
        nav.button("Settings", node_id="nav_settings", _type="button")

        main = body.main(node_id="main", _class="panels")

        users = main.section(node_id="panel_users", _class="panel")
        users.h2("Users")
        users.p("^.users", node_id="users_value")
        users.button("Refresh", node_id="users_refresh", _type="button")

        revenue = main.section(node_id="panel_revenue", _class="panel")
        revenue.h2("Revenue")
        revenue.p("^.revenue", node_id="revenue_value")
        revenue.button("Export", node_id="revenue_export", _type="button")

        footer = body.footer(node_id="footer")
        footer.span("genro-builders live demo")
