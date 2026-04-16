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
    >>> print(app.render())
"""

from typing import Any

from genro_builders.contrib.data import DataBuilder
from genro_builders.manager import ReactiveManager

from .html_builder import HtmlBuilder, HtmlRenderer


class HtmlManager(ReactiveManager):
    """HTML manager with a default DataBuilder.

    Subclass and implement ``main()`` to create an HTML app.
    The builder is available as ``self.page``. A DataBuilder named
    ``"data"`` is registered automatically — use ``^data:field``
    to reference its fields.

    Despite having two builders (page + data), ``main(source)`` is
    dispatched to the page builder for convenience.
    """

    _primary_builder: str = "page"

    def on_init(self):
        self.page = self.register_builder("page", HtmlBuilder)
        self.register_builder("data", DataBuilder)

    def setup(self) -> None:
        """Dispatch main to primary builder, main_<name> for others."""
        for name, builder in self._builders.items():
            self._current_builder_name = name
            main_method = getattr(self, f"main_{name}", None)
            if main_method is not None:
                main_method(builder.source)
            elif name == self._primary_builder:
                self.main(builder.source)
        self._current_builder_name = None

    def render(self, **kwargs: Any) -> str:
        """Render the HTML page. Calls run() automatically if needed."""
        if not len(self.page.built):
            self.run()
        return self.page.render(**kwargs)


__all__ = ["HtmlBuilder", "HtmlManager", "HtmlRenderer"]
