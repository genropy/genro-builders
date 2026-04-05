# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Contact list HTML page using declarative builder pattern.

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
          <tr>
            <td>Jane Doe</td>
            <td>jane@example.com</td>
            <td>555-5678</td>
          </tr>
          ...
        </tbody>
      </table>
    </body>
"""

from pathlib import Path

from genro_builders.contrib.html import HtmlBuilder


class ContactListPage:
    """A contact list page built with HtmlBuilder."""

    def __init__(self, contacts):
        self.contacts = contacts
        self.builder = HtmlBuilder()
        self.populate()

    def populate(self):
        """Build the page body with contacts."""
        body = self.builder.source.body()
        body.h1("Contact List")
        self.contacts_table(body, self.contacts)

    def contacts_table(self, parent, contacts):
        """Build a table from contact data."""
        table = parent.table()

        thead = table.thead()
        tr = thead.tr()
        for header in ["Name", "Email", "Phone"]:
            tr.th(header)

        tbody = table.tbody()
        for contact in contacts:
            tr = tbody.tr()
            tr.td(contact["name"])
            tr.td(contact["email"])
            tr.td(contact["phone"])

    def to_html(self, destination=None):
        """Build, render, and optionally save the page."""
        self.builder.build()
        html = self.builder.render()
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
