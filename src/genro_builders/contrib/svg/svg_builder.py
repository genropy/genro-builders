# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""SvgBuilder — SVG dialect for genro-builders.

The grammar comes from ``SvgElements`` (W3C SVG 1.1/2 schema).
Rendering lives on ``SvgRenderer``, registered under the ``"svg"``
mode in ``__init__`` (decision 6+8 v0.4.0).
"""

from __future__ import annotations

from ...builder import BagBuilderBase
from .svg_elements import SvgElements
from .svg_extensions import SvgExtensions
from .svg_renderer import SvgRenderer


class SvgBuilder(BagBuilderBase, SvgExtensions, SvgElements):
    """SVG dialect builder. Grammar only — rendering on
    ``SvgRenderer``, exposed via the ``renderer_svg`` property."""

    _name = "svg"
    _default_render_mode = "svg"

    def __init__(self) -> None:
        super().__init__()
        self.register_renderer("svg", SvgRenderer)

    @property
    def renderer_svg(self) -> SvgRenderer:
        """Fresh ``SvgRenderer`` instance bound to this builder.

        Each access returns a new instance: the renderer is meant to be
        ephemeral, used for a single ``render`` call and discarded.
        """
        return SvgRenderer(builder=self)
