# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""CompilerBase — base class for builder compilers.

A compiler walks a built bag and produces live objects (widgets,
runtime handlers, ASGI apps, ...). Each dialect declares its own
compiler subclass (``HtmlCompiler``, ``SvgCompiler``, ...) and
implements ``compile(...)``.

The compiler is owned by the ``BuilderHandler`` (one per handler,
lazy, cached) and accessible as ``handler.compiler``. The shortcut
``handler.compile(...)`` forwards to ``self.compiler.compile(...)``.

Decision 8 (renegotiated 2026-05-12): rendering and compilation live
in dedicated classes parallel to the builder; the builder only
declares grammar.

Concrete compiler implementations are deferred to a future phase.
The scaffolding is introduced now so that the handler exposes
``self.compiler`` symmetrically to ``self.renderer``.
"""

from __future__ import annotations

from typing import Any


class CompilerBase:
    """Base compiler. Subclasses override ``compile``."""

    def __init__(self, handler: Any) -> None:
        self.handler = handler

    @property
    def builder(self) -> Any:
        return self.handler.builder

    def compile(self, **kwargs: Any) -> Any:
        raise NotImplementedError(
            f"{type(self).__name__}.compile is not implemented yet; "
            "concrete compilers are planned for a future phase",
        )
