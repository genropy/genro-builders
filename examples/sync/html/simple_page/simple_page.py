# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Simple HTML page — minimal standalone builder example.

Demonstrates the basic HtmlBuilder grammar: elements, nesting, values.
For production use, wrap builders in a BuilderManager — see
contact_list for an example.

Usage:
    python simple_page.py
"""

from pathlib import Path

from genro_builders.contrib.html import HtmlBuilder

builder = HtmlBuilder()
body = builder.source.body()
body.h1("Hello World")
body.p("This is a simple paragraph.")

builder.build()
html = builder.render()

output_path = Path(__file__).with_suffix(".html")
output_path.write_text(html)
print(html)
print(f"\nSaved to {output_path}")
