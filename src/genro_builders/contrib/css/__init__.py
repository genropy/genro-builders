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
            r.selector(class_="card")

    theme = Theme()
    theme.create()
    print(theme.render())
"""

from __future__ import annotations

from ...builder import OldBuilderHandler
from .css_builder import CssBuilder


class CssBuilderHandler(OldBuilderHandler):
    """Preset handler bound to ``CssBuilder``.

    CSS rides the standard handler render flow: the universal walk turns
    each node into a dict fragment (``CssRenderer.rendered_item``) and
    ``finalize`` composes the stylesheet from those fragments (cssvar
    grouping, importcss ordering, ``@media``/``@supports``). No custom
    ``render`` override is needed.
    """

    builder_class = CssBuilder


__all__ = ["CssBuilder", "CssBuilderHandler"]
