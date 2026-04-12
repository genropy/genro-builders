# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Simple house icon composed from basic SVG shapes.

Usage:
    python house_icon.py
"""

from pathlib import Path

from genro_builders.contrib.svg import SvgBuilder

builder = SvgBuilder()
svg = builder.source.svg(
    width="120", height="120", viewBox="0 0 120 120",
    xmlns="http://www.w3.org/2000/svg",
)

svg.title("House Icon")

# Roof (triangle via polygon)
svg.polygon(points="60,10 10,60 110,60", fill="#e67e22")

# Wall
svg.rect(x="25", y="60", width="70", height="50", fill="#f39c12")

# Door
svg.rect(x="48", y="75", width="24", height="35", fill="#8e44ad", rx="3")

# Window left
svg.rect(x="32", y="72", width="14", height="14", fill="#3498db",
         stroke="#2c3e50", stroke_width="1")

# Window right
svg.rect(x="74", y="72", width="14", height="14", fill="#3498db",
         stroke="#2c3e50", stroke_width="1")

# Chimney
svg.rect(x="80", y="25", width="12", height="30", fill="#95a5a6")

builder.build()
output = builder.render()

output_path = Path(__file__).with_suffix(".svg")
output_path.write_text(output)
print(output)
print(f"\nSaved to {output_path}")
