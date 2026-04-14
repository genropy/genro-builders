# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""HTML5 builder package.

Provides HtmlBuilder for creating HTML5 documents with W3C schema validation,
and HtmlManager as the standard entry point for HTML applications.

Example:
    >>> from genro_builders.contrib.html import HtmlManager
    >>>
    >>> class HelloWorld(HtmlManager):
    ...     def main(self, source):
    ...         source.body().h1('Hello World')
    >>>
    >>> app = HelloWorld()
    >>> app.run()
    >>> print(app.page.render())
"""

from genro_builders.manager import ReactiveManager

from .html_builder import HtmlBuilder, HtmlRenderer


class HtmlManager(ReactiveManager):
    """Single-builder HTML manager.

    Subclass and implement ``store()`` / ``main()`` to create an HTML app.
    The builder is available as ``self.page``.
    """

    def __init__(self):
        self.page = self.set_builder("page", HtmlBuilder)


__all__ = ["HtmlBuilder", "HtmlManager", "HtmlRenderer"]
