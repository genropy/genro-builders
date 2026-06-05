# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""CSS-to-Python transpiler.

Reads a ``.css`` stylesheet and emits Python source that rebuilds it
with :class:`CssBuilder`. The pipeline is two trees with a walk in
between::

    .css --tree-sitter-css--> CSS tree --walk--> Python AST --ast.unparse--> .py

Gated behind the optional ``reverse`` extra (``tree-sitter-css``)::

    pip install 'genro-builders[reverse]'
"""

from __future__ import annotations

from .backend import CssTranspiler

__all__ = ["CssTranspiler"]
