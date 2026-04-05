# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0

"""Markdown report example — document with headings, tables, and code blocks.

Usage:
    python -m genro_builders.contrib.markdown.examples.markdown_report

Example output:

    # Monthly Report — March 2026

    This report summarizes the key metrics for the month.

    ## Summary

    Revenue increased by 15% compared to February.

    Customer satisfaction score: 4.7/5.0

    ## Sales by Region

    | Region | Revenue | Growth |
    | --- | --- | --- |
    | North | $120,000 | +12% |
    | South | $95,000 | +18% |
    | East | $110,000 | +8% |
    | West | $85,000 | +22% |

    ## Query Used

    ```sql
    SELECT region, SUM(amount) AS revenue
    FROM sales
    WHERE month = '2026-03'
    GROUP BY region
    ORDER BY revenue DESC;
    ```

    ## Next Steps

    - Expand marketing in West region
    - Review pricing strategy for South
    - Schedule Q2 planning meeting
"""

from __future__ import annotations

from pathlib import Path

from genro_builders.contrib.markdown import MarkdownBuilder


def build_report():
    """Build a sample Markdown report."""
    builder = MarkdownBuilder()
    doc = builder.source

    doc.h1("Monthly Report — March 2026")
    doc.p("This report summarizes the key metrics for the month.")

    # Summary section
    doc.h2("Summary")
    doc.p("Revenue increased by 15% compared to February.")
    doc.p("Customer satisfaction score: 4.7/5.0")

    # Data table
    doc.h2("Sales by Region")
    table = doc.table()

    header = table.tr()
    header.th("Region")
    header.th("Revenue")
    header.th("Growth")

    data = [
        ("North", "$120,000", "+12%"),
        ("South", "$95,000", "+18%"),
        ("East", "$110,000", "+8%"),
        ("West", "$85,000", "+22%"),
    ]
    for region, revenue, growth in data:
        row = table.tr()
        row.td(region)
        row.td(revenue)
        row.td(growth)

    # Code section
    doc.h2("Query Used")
    doc.code(
        "SELECT region, SUM(amount) AS revenue\n"
        "FROM sales\n"
        "WHERE month = '2026-03'\n"
        "GROUP BY region\n"
        "ORDER BY revenue DESC;",
        lang="sql",
    )

    # Conclusion
    doc.h2("Next Steps")

    items = doc.ul()
    items.li("Expand marketing in West region")
    items.li("Review pricing strategy for South")
    items.li("Schedule Q2 planning meeting")

    builder.build()
    return builder.render()


def demo():
    """Generate and save the report."""
    output = build_report()
    print(output)

    output_dir = Path(__file__).parent.parent.parent.parent.parent / "temp"
    output_dir.mkdir(exist_ok=True)
    path = output_dir / "monthly_report.md"
    path.write_text(output)
    print(f"\nSaved to {path}")


if __name__ == "__main__":
    demo()
