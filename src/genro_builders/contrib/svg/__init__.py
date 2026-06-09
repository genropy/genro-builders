# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""SVG contrib — SvgBuilder.

Public entry point for SVG output. Users subclass ``SvgBuilder`` and
implement ``main(self, root)``.

Example::

    from genro_builders.contrib.svg import SvgBuilder

    class MyChart(SvgBuilder):
        def main(self, root):
            svg = root.svg(viewBox="0 0 100 100")
            svg.rect(x=0, y=0, width=100, height=100, fill="red")

    chart = MyChart()
    chart.create()
    print(chart.render())
"""

from __future__ import annotations

from .svg_builder import SvgBuilder

__all__ = ["SvgBuilder"]
