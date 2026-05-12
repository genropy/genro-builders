# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""HtmlCompiler — stub.

Concrete compilation of an HTML built bag into live objects (e.g.
ASGI handlers, runtime DOM, server-side widgets) is planned for a
future phase. The class exists today so the handler can expose
``self.compiler`` symmetrically to ``self.renderer``; calling
``compile(...)`` raises ``NotImplementedError`` until the
implementation lands.
"""

from __future__ import annotations

from ...compiler import CompilerBase


class HtmlCompiler(CompilerBase):
    """HTML compiler stub. Inherits ``compile`` which raises."""
