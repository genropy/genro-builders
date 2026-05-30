# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""HtmlBuilder — HTML5 dialect for genro-builders.

The grammar comes from ``Html5Elements`` (generated from the W3C
RELAX NG schema). Rendering lives on ``HtmlRenderer``, registered
under the ``"html"`` mode in ``__init__`` (decision 6+8 v0.4.0).
"""

from __future__ import annotations

from ...builder import BagBuilderBase
from .html5_elements import Html5Elements
from .html5_extensions import Html5Extensions
from .html_renderer import HtmlRenderer


class HtmlBuilder(BagBuilderBase, Html5Extensions, Html5Elements):
    """HTML5 dialect builder. Grammar only — rendering on
    ``HtmlRenderer``, exposed via the ``renderer_html`` property."""

    _name = "html"
    _default_render_mode = "html"

    @property
    def renderer_html(self) -> HtmlRenderer:
        """Fresh ``HtmlRenderer`` instance bound to this builder.

        Each access returns a new instance: the renderer is meant to be
        ephemeral, used for a single ``render`` call and discarded.
        """
        return HtmlRenderer(builder=self)
