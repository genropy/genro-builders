# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Simple HTML page example.

Usage:
    python -m genro_builders.contrib.html.examples.simple_page

Example output:

    <body>
      <h1>Hello World</h1>
      <p>This is a simple paragraph.</p>
    </body>
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
