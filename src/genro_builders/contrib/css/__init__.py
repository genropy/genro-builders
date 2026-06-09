# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""CSS contrib — CssBuilder.

Public entry point for CSS output. Users subclass ``CssBuilder`` and
implement ``main(self, root)``.

Example::

    from genro_builders.contrib.css import CssBuilder

    class Theme(CssBuilder):
        def main(self, root):
            sheet = root.stylesheet()
            r = sheet.rule(background_color="#3498db", color="white",
                           padding="12px")
            r.selector(class_="card")

    theme = Theme()
    theme.create()
    print(theme.render())
"""

from __future__ import annotations

from .css_builder import CssBuilder

__all__ = ["CssBuilder"]
