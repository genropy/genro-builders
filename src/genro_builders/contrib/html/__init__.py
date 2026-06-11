# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""HTML contrib — HtmlBuilder.

Public entry point for HTML output. Users subclass ``HtmlBuilder`` and
implement ``main(self, root)``; a builder with no data renders on its own,
one with data is mounted on a ``BuilderHandler``.

Example::

    from genro_builders.contrib.html import HtmlBuilder

    class MyPage(HtmlBuilder):
        def main(self, root):
            root.div("hello")

    page = MyPage()
    page.create()
    print(page.render())  # '<div>hello</div>'
"""

from __future__ import annotations

from .components import HtmlComponentsBase
from .containers import HtmlContainersBase
from .html_builder import HtmlBuilder

__all__ = ["HtmlBuilder", "HtmlComponentsBase", "HtmlContainersBase"]
