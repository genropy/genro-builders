# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""03 — HtmlManager: separating data from structure.

What you learn:
    - HtmlManager coordinates a builder with a shared data store
    - store(data): populate shared data (called first)
    - main(source): build the HTML structure (called second)
    - render(): auto-runs setup + build if needed
    - No super().__init__() needed — handled by __init_subclass__

Prerequisites: 02_static_page

Usage:
    python 03_builder_manager.py
"""
from __future__ import annotations

from pathlib import Path

from genro_builders.contrib.html import HtmlManager


class ContactList(HtmlManager):
    """A contact list page. Data and structure are separate."""

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
            .page { font-family: sans-serif; max-width: 600px; margin: 2em auto;
                    color: #333; background: #fff; padding: 1.5em; border-radius: 8px; }
            table { width: 100%; border-collapse: collapse; }
            th, td { padding: 0.5em; text-align: left; border-bottom: 1px solid #ddd; }
            th { background: #f0f4f8; color: #1e293b; }
            h1 { color: #1e293b; }
        """)

        body = source.body()
        page = body.div(_class="page")
        page.h1("Team Contacts")

        contacts = self.reactive_store["contacts"]

        table = page.table()
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
html = app.render()

output = Path(__file__).with_suffix(".html")
output.write_text(html)
print(html)
print(f"\nSaved to {output}")
