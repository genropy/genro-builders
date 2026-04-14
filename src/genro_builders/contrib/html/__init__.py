# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""HTML5 builder package.

Provides HtmlBuilder for creating HTML5 documents with W3C schema validation,
and HtmlManager as the standard entry point for HTML applications.

Example:
    >>> from genro_builders.contrib.html import HtmlManager
    >>>
    >>> class HelloWorld(HtmlManager):
    ...     def main(self, html):
    ...         html.body().h1('Hello World')
    >>>
    >>> print(HelloWorld().render())
"""

from typing import Any

from genro_builders.manager import ReactiveManager

from .html_builder import HtmlBuilder, HtmlRenderer


class HtmlManager(ReactiveManager):
    """Single-builder HTML manager.

    Subclass and implement ``main(html)`` to populate the document.
    The ``html`` parameter is the root ``<html>`` node — add
    ``head()`` and ``body()`` as children.

    The builder is available as ``self.page``.
    """

    def __init__(self):
        self.page = self.set_builder("page", HtmlBuilder)

    def setup(self) -> None:
        """Populate data and source with <html> root node."""
        self.store(self.reactive_store)
        html_node = self.page.source.html()
        self.main(html_node)

    def main(self, html: Any) -> None:
        """Override to populate the HTML document."""

    def render(self, **kwargs: Any) -> str:
        """Render the HTML page. Calls run() automatically if needed."""
        if not len(self.page.built):
            self.run()
        return self.page.render(**kwargs)


__all__ = ["HtmlBuilder", "HtmlManager", "HtmlRenderer"]
