# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""SVG builder package.

Provides SvgBuilder for creating SVG documents with element validation,
and SvgManager as the standard entry point for SVG applications.

Example:
    >>> from genro_builders.contrib.svg import SvgManager
    >>>
    >>> class MyChart(SvgManager):
    ...     def main(self, source):
    ...         svg = source.svg(width="200", height="200")
    ...         svg.circle(cx="100", cy="100", r="80", fill="coral")
    >>>
    >>> app = MyChart()
    >>> app.run()
    >>> print(app.render())
"""

from typing import Any

from genro_builders.manager import ReactiveManager

from .svg_builder import SvgBuilder, SvgRenderer


class SvgManager(ReactiveManager):
    """Single-builder SVG manager.

    Subclass and implement ``store()`` / ``main()`` to create an SVG app.
    The builder is available as ``self.page``.
    """

    def __init__(self):
        self.page = self.set_builder("page", SvgBuilder)

    def render(self, **kwargs: Any) -> str:
        """Render the SVG document. Calls run() automatically if needed."""
        if not len(self.page.built):
            self.run()
        return self.page.render(**kwargs)


__all__ = ["SvgBuilder", "SvgManager", "SvgRenderer"]
