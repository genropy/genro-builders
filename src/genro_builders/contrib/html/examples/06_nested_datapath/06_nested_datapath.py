# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""06 — Nested datapath. See README.md for the walkthrough."""
from __future__ import annotations

from pathlib import Path

from genro_builders import SourceBag
from genro_builders.contrib.html import HtmlBuilderHandler

_USERS = [
    {"id": "alice", "name": "Alice", "role": "Designer"},
    {"id": "bob", "name": "Bob", "role": "Engineer"},
    {"id": "carol", "name": "Carol", "role": "Manager"},
]


class Section1(HtmlBuilderHandler):
    """One nested scope: a card whose inner pointers read a sub-bag."""

    def setup(self):
        self.data.set_item("team.alice", SourceBag(_USERS[0]))

    def main(self, root):
        body = root.body(datapath="team")
        card = body.div(datapath=".alice", class_="card")
        card.h3("^.name")
        card.span("^.role")


class Section2(HtmlBuilderHandler):
    """Repeated nested scopes: one card per user, each pointer-bound."""

    def setup(self):
        for user in _USERS:
            self.data.set_item(f"team.{user['id']}", SourceBag(user))

    def main(self, root):
        body = root.body(datapath="team")
        grid = body.div(class_="grid")
        for user in self.data["team"]:
            card = grid.div(datapath=f".{user.label}", class_="card")
            card.h3("^.name")
            card.span("^.role")


def _render_section(handler_cls, *, pretty=True):
    page = handler_cls()
    page.create()
    return page.render(pretty=pretty)


if __name__ == "__main__":
    sections = [Section1, Section2]
    parts = []
    for i, cls in enumerate(sections, 1):
        parts.append(f"<!-- Section {i} -->")
        parts.append(_render_section(cls))
        parts.append("")
    rendered = "\n".join(parts)

    output = Path(__file__).with_suffix(".html")
    output.write_text(rendered)
    print(rendered)
    print(f"Saved to {output}")
