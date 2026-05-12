# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""CssBuilder — CSS dialect for genro-builders (level 1).

Level 1 grammar covers ``rule`` (selector + property declarations)
and ``cssvar`` (CSS custom property declarations) plus an optional
top-level ``stylesheet`` container. At-rules (``@media``,
``@keyframes``, ``@supports``, ...) and rule nesting are out of
scope and will be handled by a dedicated future subtask.

The grammar lives in ``CssElements``. Rendering lives on
``CssRenderer`` (``render_css`` method). Compilation (future) lives
on ``CssCompiler``. The builder only wires them together
(decision 8, renegotiated 2026-05-12).

The class-level ``_name`` attribute marks the dialect for the
forthcoming builder registry (see
``temp/subtask/subbuilder/builder_registration_guide.md``). The
attribute is ignored by the current ``BagBuilderBase.__init_subclass__``
in develop; it becomes active once the registry lands.
"""

from __future__ import annotations

from ...builder import BagBuilderBase
from .css_compiler import CssCompiler
from .css_elements import CssElements
from .css_renderer import CssRenderer


class CssBuilder(BagBuilderBase, CssElements):
    """CSS dialect builder. Grammar only — rendering on ``CssRenderer``,
    compilation (future) on ``CssCompiler``."""

    _name = "css"
    _default_render_mode = "css"
    _renderer_class = CssRenderer
    _compiler_class = CssCompiler
