# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""05 — Pointers and templates. See README.md for the walkthrough."""
from __future__ import annotations

from pathlib import Path

from genro_builders.contrib.html import HtmlBuilderHandler


class Section1(HtmlBuilderHandler):
    """A pointer as the node value, and a pointer as an attribute."""

    def setup(self):
        self.data.set_item("page.title", "Hello")
        self.data.set_item("page.color", "#e74c3c")

    def main(self, root):
        body = root.body(datapath="page")
        body.h1("^.title")
        body.div("boxed", color="^.color", border="1px solid")


class Section2(HtmlBuilderHandler):
    """``^`` (lazy) and ``=`` (eager) read the same value at render."""

    def setup(self):
        self.data.set_item("page.color", "#3498db")

    def main(self, root):
        body = root.body(datapath="page")
        body.div("lazy ^", color="^.color")
        body.div("eager =", color="=.color")


class Section3(HtmlBuilderHandler):
    """A ``${name}`` template weaves a resolved attribute into a string."""

    def setup(self):
        self.data.set_item("page.color", "danger")

    def main(self, root):
        body = root.body(datapath="page")
        body.div("themed", class_="card ${color}", color="^.color")


class Section4(HtmlBuilderHandler):
    """A pointer to a missing datum resolves to None (empty in output)."""

    def setup(self):
        self.data.set_item("page.title", "Present")

    def main(self, root):
        body = root.body(datapath="page")
        body.p("Title: ").span("^.title")
        body.p("Missing: ").span("^.subtitle")


def _render_section(handler_cls, *, pretty=True):
    page = handler_cls()
    page.create()
    return page.render(pretty=pretty)


if __name__ == "__main__":
    sections = [Section1, Section2, Section3, Section4]
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
