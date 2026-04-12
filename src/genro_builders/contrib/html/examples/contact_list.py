# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Contact list HTML page using BuilderManager pattern.

Usage:
    python -m genro_builders.contrib.html.examples.contact_list

Example output:

    <body>
      <h1>Contact List</h1>
      <table>
        <thead>
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Phone</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>John Smith</td>
            <td>john@example.com</td>
            <td>555-1234</td>
          </tr>
          ...
        </tbody>
      </table>
    </body>
"""

from __future__ import annotations

from pathlib import Path

from genro_builders.contrib.html import HtmlBuilder
from genro_builders.manager import BuilderManager


class ContactListPage(BuilderManager):
    """A contact list page coordinated by BuilderManager."""

    def __init__(self, contacts):
        self.contacts = contacts
        self.page = self.set_builder("page", HtmlBuilder)
        self.run()

    def store(self, data):
        """Populate shared data with contact records."""
        for i, contact in enumerate(self.contacts):
            for key, value in contact.items():
                data[f"contacts.{i}.{key}"] = value

    def main(self, source):
        """Build the page body with contacts table."""
        body = source.body()
        body.h1("Contact List")
        self._contacts_table(body)

    def _contacts_table(self, parent):
        """Build a table from contact data."""
        table = parent.table()

        thead = table.thead()
        tr = thead.tr()
        for header in ["Name", "Email", "Phone"]:
            tr.th(header)

        tbody = table.tbody()
        for contact in self.contacts:
            tr = tbody.tr()
            tr.td(contact["name"])
            tr.td(contact["email"])
            tr.td(contact["phone"])

    def to_html(self, destination=None):
        """Render and optionally save the page."""
        html = self.page.render()
        if destination is not None:
            Path(destination).write_text(html)
        return html


if __name__ == "__main__":
    contacts = [
        {"name": "John Smith", "email": "john@example.com", "phone": "555-1234"},
        {"name": "Jane Doe", "email": "jane@example.com", "phone": "555-5678"},
        {"name": "Bob Wilson", "email": "bob@example.com", "phone": "555-9012"},
    ]

    page = ContactListPage(contacts)

    destination = Path(__file__).with_suffix(".html")
    html = page.to_html(destination=destination)
    print(html)
