# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""01 — Hello World: the simplest possible builder.

What you learn:
    - Instantiate HtmlBuilder
    - Access the source Bag via builder.source
    - Add elements (body, h1, p)
    - Call build() to materialize source → built
    - Call render() to produce HTML string
    - Save output to file

Prerequisites: None. This is the starting point.

Usage:
    python 01_hello_world.py
"""
from __future__ import annotations

from pathlib import Path

from genro_builders.contrib.html import HtmlBuilder

# Create a builder — this gives us the full HTML5 grammar
builder = HtmlBuilder()

# builder.source is where we describe the structure
body = builder.source.body()
body.h1("Hello World")
body.p("This is my first builder page.")

# build() materializes source → built (expands components, resolves pointers)
builder.build()

# render() serializes the built Bag to an HTML string
html = builder.render()

# Save to file
output = Path(__file__).with_suffix(".html")
output.write_text(html)
print(html)
print(f"\nSaved to {output}")
