# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Signup demo: a form with inputs, a select and a textarea."""

from __future__ import annotations

from ..interactive_demo import InteractiveDemo

DEMO_TITLE = "Signup form"


class Demo(InteractiveDemo):
    """A form with text inputs, a select and a textarea, bound to data.

    Data lives under ``form``: ``form.name``, ``form.email``,
    ``form.role``, ``form.bio``.
    """

    def setup(self):
        self.set_data("form.heading", "Create your account")
        self.set_data("form.name", "")
        self.set_data("form.email", "")
        self.set_data("form.bio", "")

    def main(self, root):
        body = root.body(datapath="form", node_id="body")
        body.link(rel="stylesheet", href="demo_css")
        body.h1("^.heading", node_id="heading")

        f = body.form(node_id="form")

        f.input(value="^.name", node_id="name", _type="text",
                placeholder="Name")
        f.input(value="^.email", node_id="email", _type="email",
                placeholder="Email")

        role = f.select(node_id="role")
        role.option("Viewer", value="viewer")
        role.option("Editor", value="editor")
        role.option("Admin", value="admin")

        f.textarea("^.bio", node_id="bio", placeholder="Short bio")
        f.button("Sign up", node_id="submit", _type="submit")
