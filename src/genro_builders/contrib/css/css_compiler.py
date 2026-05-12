# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""CssCompiler — stub.

Concrete compilation of a CSS built bag into runtime artefacts (e.g.
a parsed AST, a CSSOM-like structure) is out of scope for level 1.
The class exists so the handler can expose ``self.compiler``
symmetrically to ``self.renderer``; calling ``compile(...)`` raises
``NotImplementedError`` until a real implementation lands.
"""

from __future__ import annotations

from ...compiler import CompilerBase


class CssCompiler(CompilerBase):
    """CSS compiler stub. Inherits ``compile`` which raises."""
