# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Card with drop shadow filter.

Usage:
    python card_shadow.py
"""

from pathlib import Path

from genro_builders.contrib.svg import SvgBuilder

builder = SvgBuilder()
svg = builder.source.svg(
    width="200", height="160", viewBox="0 0 200 160",
    xmlns="http://www.w3.org/2000/svg",
)

# Filter definition
defs = svg.defs()
f = defs.filter(id="shadow", x="-20%", y="-20%", width="140%", height="140%")
f.feGaussianBlur(stdDeviation="4", result="blur")
f.feOffset(dx="4", dy="4", result="offsetBlur")

merge = f.feMerge()
merge.feMergeNode(in_="offsetBlur")
merge.feMergeNode(in_="SourceGraphic")

# Card with shadow
svg.rect(x="30", y="20", width="140", height="100", rx="8",
         fill="white", stroke="#ddd", stroke_width="1", filter="url(#shadow)")

svg.text("Card Title", x="100", y="60",
         text_anchor="middle", font_size="16", font_weight="bold", fill="#333")
svg.text("With drop shadow", x="100", y="85",
         text_anchor="middle", font_size="12", fill="#999")

builder.build()
output = builder.render()

output_path = Path(__file__).with_suffix(".svg")
output_path.write_text(output)
print(output)
print(f"\nSaved to {output_path}")
