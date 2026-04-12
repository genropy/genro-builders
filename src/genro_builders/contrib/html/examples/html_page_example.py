# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0

"""Example: Shopping list and contacts table using HtmlBuilder.

Demonstrates standalone builder usage for quick prototyping.
For production use, wrap builders in a BuilderManager — see
contact_list.py for an example.

Usage:
    python -m genro_builders.contrib.html.examples.html_page_example

Example output (abbreviated):

    <body>
      <div id="page">
        <div id="header">
          <h1>Welcome</h1>
          <h2>Page subtitle</h2>
        </div>
        <div id="content">
          <h3>Shopping List</h3>
          <ul>
            <li>Bread</li>
            <li>Milk</li>
            <li>Eggs</li>
          </ul>
          <h3>Contacts</h3>
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
                <td>555-1234567</td>
              </tr>
              ...
            </tbody>
          </table>
        </div>
        <div id="footer">
          <span>(c) 2025 - All rights reserved</span>
        </div>
      </div>
    </body>
"""

from __future__ import annotations

from pathlib import Path

from genro_builders.contrib.html import HtmlBuilder


def build_page():
    """Build the page content using HtmlBuilder."""
    builder = HtmlBuilder()
    body = builder.source.body()
    page_div = body.div(id="page")

    # Header
    header = page_div.div(id="header")
    header.h1("Welcome")
    header.h2("Page subtitle")

    # Content
    content = page_div.div(id="content")

    # Shopping list
    content.h3("Shopping List")
    lista = content.ul()
    lista.li("Bread")
    lista.li("Milk")
    lista.li("Eggs")

    # Contacts table
    content.h3("Contacts")
    table = content.table()

    thead = table.thead()
    tr = thead.tr()
    tr.th("Name")
    tr.th("Email")
    tr.th("Phone")

    tbody = table.tbody()
    for name, email, phone in [
        ("John Smith", "john@example.com", "555-1234567"),
        ("Jane Doe", "jane@example.com", "555-7654321"),
    ]:
        row = tbody.tr()
        row.td(name)
        row.td(email)
        row.td(phone)

    # Footer
    footer = page_div.div(id="footer")
    footer.span("(c) 2025 - All rights reserved")

    return builder


def demo():
    """Demo of HtmlBuilder."""
    builder = build_page()
    builder.build()
    html = builder.render()
    print(html)

    # Save to file
    output_path = Path(__file__).parent / "example.html"
    output_path.write_text(html)
    print(f"\nSaved to: {output_path}")


if __name__ == "__main__":
    demo()
