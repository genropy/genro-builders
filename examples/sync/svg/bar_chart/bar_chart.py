# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Horizontal bar chart with gradient fill and labels.

Usage:
    python bar_chart.py
"""

from pathlib import Path

from genro_builders.contrib.svg import SvgBuilder

builder = SvgBuilder()
svg = builder.source.svg(
    width="400", height="260", viewBox="0 0 400 260",
    xmlns="http://www.w3.org/2000/svg",
)

svg.title("Monthly Sales")

# Gradient definition
defs = svg.defs()
grad = defs.linearGradient(id="barGrad", x1="0", y1="0", x2="1", y2="0")
grad.stop(offset="0%", stop_color="#4facfe")
grad.stop(offset="100%", stop_color="#00f2fe")

# Data
data = [
    ("Jan", 120), ("Feb", 90), ("Mar", 150),
    ("Apr", 80), ("May", 200), ("Jun", 170),
]
bar_h = 30
gap = 8
max_val = max(v for _, v in data)
chart_w = 280

# Chart group
chart = svg.g(transform="translate(80, 30)")

for i, (label, value) in enumerate(data):
    y = i * (bar_h + gap)
    w = int(value / max_val * chart_w)

    chart.rect(x="0", y=str(y), width=str(w), height=str(bar_h),
               fill="url(#barGrad)", rx="4")
    chart.text(str(value), x=str(w + 8), y=str(y + 20),
               font_size="14", fill="#333")
    chart.text(label, x="-10", y=str(y + 20),
               font_size="14", fill="#666", text_anchor="end")

builder.build()
output = builder.render()

output_path = Path(__file__).with_suffix(".svg")
output_path.write_text(output)
print(output)
print(f"\nSaved to {output_path}")
