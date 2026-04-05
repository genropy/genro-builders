# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Simple HTML page example."""

from pathlib import Path

from genro_builders.builder_bag import BuilderBag as Bag
from genro_builders.contrib.html import HtmlBuilder

page = Bag(builder=HtmlBuilder)
head = page.head()
head.title(value="Simple Page")

body = page.body()
body.h1(value="Hello World")
body.p(value="This is a simple paragraph.")

page.builder.build()
html = page.builder.render()

output_path = Path(__file__).with_suffix(".html")
output_path.write_text(html)
print(html)
