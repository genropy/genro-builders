# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""SVG builder package.

Provides SvgBuilder for creating SVG documents with element validation.

Example:
    >>> from genro_builders.contrib.svg import SvgBuilder
    >>>
    >>> builder = SvgBuilder()
    >>> svg = builder.source.svg(width="200", height="200")
    >>> svg.circle(cx="100", cy="100", r="80", fill="coral")
    >>> builder.build()
    >>> print(builder.render())
"""

from .svg_builder import SvgBuilder, SvgRenderer

__all__ = ["SvgBuilder", "SvgRenderer"]
