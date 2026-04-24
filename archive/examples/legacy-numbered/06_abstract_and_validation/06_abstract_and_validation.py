# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""06 — Structural validation: the HTML5 schema at work.

What you learn:
    - HtmlBuilder enforces W3C HTML5 nesting rules at insertion time
    - Each HTML5 element declares which children it accepts (sub_tags)
    - Invalid nesting raises ValueError immediately
    - validate() checks the whole built tree for structural issues

Important principle:
    When extending HtmlBuilder, custom tags are ALWAYS @component
    (with main_tag), NEVER @element. The @element decorator defines
    schema primitives (the 112 HTML5 tags). User extensions are
    composite structures that expand into real HTML tags — that is
    exactly what @component does.

    An @element('panel') on HtmlBuilder would produce <panel> in the
    output — an invalid HTML tag that browsers and compilers cannot
    handle. A @component(main_tag='div') instead expands into real
    <div>, <p>, <h3> tags that work everywhere.

Prerequisites: 05_components

Usage:
    python 06_abstract_and_validation.py
"""
from __future__ import annotations

from pathlib import Path

from genro_builders.contrib.html import HtmlBuilder

builder = HtmlBuilder()
s = builder.source

head = s.head()
head.title("Validation Demo")
head.style("""
    body { font-family: sans-serif; max-width: 600px; margin: 2em auto; }
    table { border-collapse: collapse; width: 100%; margin: 1em 0; }
    th, td { padding: 0.5em; border: 1px solid #ddd; text-align: left; }
    th { background: #f0f4f8; }
    code { background: #fee; padding: 0.2em 0.4em; border-radius: 3px; }
""")

body = s.body()
body.h1("HTML5 Structural Validation")
body.p("HtmlBuilder enforces W3C nesting rules. Valid structures work:")

# --- Valid nesting ---
# ul > li
ul = body.ul()
ul.li("Item 1")
ul.li("Item 2")

# table > thead > tr > th / tbody > tr > td
table = body.table()
thead = table.thead()
header = thead.tr()
header.th("Name")
header.th("Value")
tbody = table.tbody()
row = tbody.tr()
row.td("Alpha")
row.td("100")

# div > p, h2, section (all flow content)
section = body.section()
section.h2("Section Title")
section.p("Section content.")

builder.build()
html = builder.render()

output = Path(__file__).with_suffix(".html")
output.write_text(html)

# --- Invalid nesting: caught at insertion time ---
print("=== HTML5 Validation Demo ===\n")
print("Valid structure built successfully.\n")
print("Invalid nesting caught at insertion time:\n")

cases = [
    ("div > tr", lambda: HtmlBuilder().source.body().div().tr()),
    ("tbody > td", lambda: HtmlBuilder().source.body().table().tbody().td("x")),
    ("div > li", lambda: HtmlBuilder().source.body().div().li("x")),
    ("p > div", lambda: HtmlBuilder().source.body().p().div()),
]

for label, fn in cases:
    try:
        fn()
        print(f"  {label}: (no error — unexpected)")
    except ValueError as e:
        print(f"  {label}: {e}")

print(f"\n{html}")
print(f"\nSaved to {output}")
