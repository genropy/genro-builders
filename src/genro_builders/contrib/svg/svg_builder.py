# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""SvgBuilder — SVG dialect for genro-builders.

The grammar comes from ``SvgElements`` (W3C SVG 1.1/2 schema).
Rendering lives on ``SvgRenderer``; compilation (future) on
``SvgCompiler``. The builder only wires them together (decision 8,
renegotiated 2026-05-12).
"""

from __future__ import annotations

from ...builder import BagBuilderBase
from .svg_compiler import SvgCompiler
from .svg_elements import SvgElements
from .svg_renderer import SvgRenderer


class SvgBuilder(BagBuilderBase, SvgElements):
    """SVG dialect builder. Grammar only — rendering is on
    ``SvgRenderer``, compilation (future) on ``SvgCompiler``."""

    _default_render_mode = "svg"
    _renderer_class = SvgRenderer
    _compiler_class = SvgCompiler
