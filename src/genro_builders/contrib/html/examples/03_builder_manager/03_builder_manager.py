# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""03 — BuilderManager: separating data from structure.

What you learn:
    - BuilderManager coordinates builders with a shared data store
    - store(data): populate shared data (called first)
    - main(source): build the HTML structure (called second)
    - set_builder(): register a builder by name
    - run(): orchestrates setup + build in one call
    - No super().__init__() needed — handled by __init_subclass__

Prerequisites: 02_static_page

Usage:
    python 03_builder_manager.py
"""
from __future__ import annotations

from pathlib import Path

from genro_builders.contrib.html import HtmlBuilder
from genro_builders.manager import BuilderManager


class ContactList(BuilderManager):
    """A contact list page. Data and structure are separate."""

    def __init__(self):
        self.page = self.set_builder("page", HtmlBuilder)
        self.run()

    def store(self, data):
        """Populate shared data. Called before main()."""
        data["contacts"] = [
            {"name": "Alice Johnson", "email": "alice@example.com", "role": "Engineer"},
            {"name": "Bob Smith", "email": "bob@example.com", "role": "Designer"},
            {"name": "Carol White", "email": "carol@example.com", "role": "Manager"},
        ]

    def main(self, source):
        """Build the HTML structure using data from store()."""
        head = source.head()
        head.title("Contact List")
        head.style("""
            body { font-family: sans-serif; max-width: 600px; margin: 2em auto; }
            table { width: 100%; border-collapse: collapse; }
            th, td { padding: 0.5em; text-align: left; border-bottom: 1px solid #ddd; }
            th { background: #f0f4f8; }
        """)

        body = source.body()
        body.h1("Team Contacts")

        # Access data from the reactive store
        contacts = self.reactive_store["contacts"]

        table = body.table()
        thead = table.thead()
        header = thead.tr()
        header.th("Name")
        header.th("Email")
        header.th("Role")

        tbody = table.tbody()
        for contact in contacts:
            row = tbody.tr()
            row.td(contact["name"])
            row.td().a(contact["email"], href=f"mailto:{contact['email']}")
            row.td(contact["role"])


app = ContactList()
html = app.page.render()

output = Path(__file__).with_suffix(".html")
output.write_text(html)
print(html)
print(f"\nSaved to {output}")
