# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Target-like concentric circles with alternating colors.

Usage:
    python concentric_circles.py
"""

from pathlib import Path

from genro_builders.contrib.svg import SvgBuilder

builder = SvgBuilder()
svg = builder.source.svg(
    width="200", height="200", viewBox="0 0 200 200",
    xmlns="http://www.w3.org/2000/svg",
)

svg.title("Target")

colors = ["#e74c3c", "#ffffff", "#e74c3c", "#ffffff", "#e74c3c"]
radii = [90, 72, 54, 36, 18]

for r, color in zip(radii, colors, strict=True):
    svg.circle(cx="100", cy="100", r=str(r), fill=color,
               stroke="#c0392b", stroke_width="2")

builder.build()
output = builder.render()

output_path = Path(__file__).with_suffix(".svg")
output_path.write_text(output)
print(output)
print(f"\nSaved to {output_path}")
