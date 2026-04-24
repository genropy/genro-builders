# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""03 — HtmlManager: separating data from structure.

What you learn:
    - HtmlManager coordinates a builder with a shared data store
    - Data lives in external files (JSON), loaded at runtime
    - CSS lives in external files, loaded via style tag
    - main(source): defines only the HTML structure
    - render(): auto-runs setup + build if needed

Prerequisites: 02_static_page

Usage:
    python 03_builder_manager.py
"""
from __future__ import annotations

from pathlib import Path

from genro_bag.resolvers import FileResolver

from genro_builders.contrib.html import HtmlManager

HERE = Path(__file__).parent


class ContactList(HtmlManager):
    """A contact list page. Data and structure are separate."""

    def main(self, source):
        """Build the HTML structure — data comes from outside."""
        head = source.head()
        head.title("Contact List")
        # FileResolver: pull model — content loaded on demand at render time
        head.style(FileResolver("style.css", base_path=str(HERE)))

        body = source.body()
        page = body.div(_class="page")
        page.h1("Team Contacts")

        contacts = self.local_store()["contacts"]

        table = page.table()
        thead = table.thead()
        header = thead.tr()
        header.th("Name")
        header.th("Email")
        header.th("Role")

        tbody = table.tbody()
        for contact in contacts:
            row = tbody.tr()
            row.td(contact.attr.get("name"))
            row.td(contact.attr.get("email"))
            row.td(contact.attr.get("role"))


app = ContactList()
# FileResolver with as_bag=True: JSON is parsed into a Bag on first access.
# The Bag node format (label/value/attr) is preserved — perfect for iterate.
app.local_store("page").set_resolver(
    "contacts", FileResolver("contacts.json", as_bag=True, base_path=str(HERE)),
)
html = app.render()

output = HERE / "03_builder_manager.html"
output.write_text(html)
print(html)
print(f"\nSaved to {output}")
