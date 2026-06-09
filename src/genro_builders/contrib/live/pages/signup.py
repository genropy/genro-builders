# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Signup demo: a form with inputs, a select and a textarea."""

from __future__ import annotations

from ..interactive_demo import InteractiveDemo

DEMO_TITLE = "Signup form"


class Demo(InteractiveDemo):
    """A form with text inputs, a select and a textarea, bound to data.

    Data lives under ``form``: ``form.name``, ``form.email``, ``form.bio``.
    The point here is the variety of form controls, each bound to data with
    a ``^`` pointer. No node is named: nothing looks one up afterwards, so
    none carries a ``node_id`` or ``node_label`` (see ``dashboard`` for when
    you would). The ``<select>`` is the one structural subtree — its
    ``<option>`` children carry the values the select will offer.
    """

    def setup(self, data):
        self.set_data("form.heading", "Create your account")
        self.set_data("form.name", "")
        self.set_data("form.email", "")
        self.set_data("form.bio", "")

    def main(self, root):
        body = root.body(datapath="form")
        body.link(rel="stylesheet", href="demo_css")
        body.h1("^.heading")

        f = body.form()

        f.input(value="^.name", placeholder="Name")
        f.input(value="^.email", html_type="email", placeholder="Email")

        role = f.select()
        role.option("Viewer", value="viewer")
        role.option("Editor", value="editor")
        role.option("Admin", value="admin")

        f.textarea("^.bio", placeholder="Short bio")
        f.button("Sign up", html_type="submit")
