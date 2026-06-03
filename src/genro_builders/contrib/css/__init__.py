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
    print(theme.render())
"""

from __future__ import annotations

from ...builder_handler import BuilderHandler
from .css_builder import CssBuilder


class CssBuilderHandler(BuilderHandler):
    """Preset handler bound to ``CssBuilder``.

    CSS is rendered as a whole stylesheet (cssvar grouping, importcss
    ordering), not node-by-node, so ``render`` drives the renderer's
    own top-level walk on the full source instead of the generic
    ``render_children``. A partial (single-node) render is not
    meaningful for CSS.
    """

    builder_class = CssBuilder

    def render(self, startnode=None, mode=None, target=None, **opts):
        renderer = self._get_renderer(mode)
        result = renderer.render(self.source, **opts)
        return renderer.finalize(result, self._get_target(target, renderer))


__all__ = ["CssBuilder", "CssBuilderHandler"]
