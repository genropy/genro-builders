# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""CSS contrib — CssBuilder + CssBuilderHandler.

Public entry point for CSS output. Users subclass
``CssBuilderHandler`` and implement ``main(self, root)``.

Example::

    from genro_builders.contrib.css import CssBuilderHandler

    class Theme(CssBuilderHandler):
        def main(self, root):
            sheet = root.stylesheet()
            r = sheet.rule(background_color="#3498db", color="white",
                           padding="12px")
            r.selector(_class="card")

    theme = Theme()
    theme.create()
    theme.build()
    print(theme.render())
"""

from __future__ import annotations

from ...builder_handler import BuilderHandler
from .css_builder import CssBuilder


class CssBuilderHandler(BuilderHandler):
    """Preset handler bound to ``CssBuilder``."""

    builder_class = CssBuilder


__all__ = ["CssBuilder", "CssBuilderHandler"]
