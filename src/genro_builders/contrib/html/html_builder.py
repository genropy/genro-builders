# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""HtmlBuilder — HTML5 dialect for genro-builders.

The grammar comes from ``Html5Elements`` (generated from the W3C
RELAX NG schema). Rendering lives on ``HtmlRenderer``; compilation
(future) on ``HtmlCompiler``. The builder only wires them together
(decision 8, renegotiated 2026-05-12).
"""

from __future__ import annotations

from ...builder import BagBuilderBase
from .html5_elements import Html5Elements
from .html_compiler import HtmlCompiler
from .html_renderer import HtmlRenderer


class HtmlBuilder(BagBuilderBase, Html5Elements):
    """HTML5 dialect builder. Grammar only — rendering is on
    ``HtmlRenderer``, compilation (future) on ``HtmlCompiler``."""

    _default_render_mode = "html"
    _renderer_class = HtmlRenderer
    _compiler_class = HtmlCompiler
