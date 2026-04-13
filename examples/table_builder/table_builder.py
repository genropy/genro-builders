# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0

"""TableBuilder — defining a custom builder from scratch.

Demonstrates:
- Using @element decorator with sub_tags for structure validation
- Building HTML tables with thead, tbody, tr, th, td
- Cardinality constraints (thead[:1] = at most one)

This is a standalone builder (no HtmlBuilder dependency).
For production use, wrap builders in a BuilderManager.

Usage:
    python table_builder.py
"""

from __future__ import annotations

from pathlib import Path

from genro_builders import BagBuilderBase
from genro_builders.builder_bag import BuilderBag as Bag
from genro_builders.builder import element


class TableBuilder(BagBuilderBase):
    """Builder for HTML table elements."""

    @element(sub_tags="caption[:1], thead[:1], tbody, tfoot[:1], tr")
    def table(self): ...

    @element()
    def caption(self): ...

    @element(sub_tags="tr")
    def thead(self): ...

    @element(sub_tags="tr")
    def tbody(self): ...

    @element(sub_tags="tr")
    def tfoot(self): ...

    @element(sub_tags="th, td")
    def tr(self): ...

    @element()
    def th(self): ...

    @element()
    def td(self): ...


def render_node(node, indent=0):
    """Simple recursive HTML renderer."""
    tag = node.node_tag or node.label
    spaces = "  " * indent

    node_value = node.get_value(static=True)
    if not isinstance(node_value, Bag):
        if node_value == "":
            return f"{spaces}<{tag} />"
        return f"{spaces}<{tag}>{node_value}</{tag}>"

    lines = [f"{spaces}<{tag}>"]
    for child in node_value:
        lines.append(render_node(child, indent + 1))
    lines.append(f"{spaces}</{tag}>")
    return "\n".join(lines)


if __name__ == "__main__":
    store = Bag(builder=TableBuilder)
    table = store.table()

    # Header
    thead = table.thead()
    header_row = thead.tr()
    header_row.th("Product")
    header_row.th("Price")
    header_row.th("Quantity")

    # Body
    tbody = table.tbody()
    for product, price, qty in [
        ("Widget", "$10.00", "5"),
        ("Gadget", "$25.00", "3"),
        ("Gizmo", "$15.00", "8"),
    ]:
        row = tbody.tr()
        row.td(product)
        row.td(price)
        row.td(qty)

    # Render
    table_node = store.get_node("table_0")
    html = render_node(table_node)

    output_path = Path(__file__).with_suffix(".html")
    output_path.write_text(html)
    print(html)
    print(f"\nSaved to {output_path}")
