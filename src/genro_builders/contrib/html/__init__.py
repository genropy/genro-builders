# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""HTML contrib — HtmlBuilder.

Public entry point for HTML output. Users subclass ``HtmlBuilder`` and
implement ``main(self, root)``; the builder owns its own datastore
(``builder.data``), so one with data needs nothing extra.

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

from .demo_collection import DemoComponents, DemoContainers
from .html_builder import HtmlBuilder

__all__ = ["DemoComponents", "DemoContainers", "HtmlBuilder"]
