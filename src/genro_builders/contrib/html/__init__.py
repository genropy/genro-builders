# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""HTML contrib — HtmlBuilder + HtmlBuilderHandler.

Public entry point for HTML output. Users subclass
``HtmlBuilderHandler`` and implement ``main(self, root)``.

Example::

    from genro_builders.contrib.html import HtmlBuilderHandler

    class MyPage(HtmlBuilderHandler):
        def main(self, root):
            root.div("hello")

    page = MyPage()
    page.create()
    print(page.render())  # '<div>hello</div>'
"""

from __future__ import annotations

from ...builder import OldBuilderHandler
from .html_builder import HtmlBuilder


class HtmlBuilderHandler(OldBuilderHandler):
    """Preset handler bound to ``HtmlBuilder`` (decision 9)."""

    builder_class = HtmlBuilder


__all__ = ["HtmlBuilder", "HtmlBuilderHandler"]
