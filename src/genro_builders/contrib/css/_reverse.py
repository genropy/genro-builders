# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Reverse: parse CSS source and emit equivalent CssBuilder Python.

Pipeline: ``tree-sitter-css`` parses the CSS source into an AST; a
visitor (``CssReverser``, added in a later phase) walks it and builds a
Python ``ast.Module`` calling the CssBuilder API; ``ast.unparse``
serializes that to Python source.

This module is gated behind the optional ``reverse`` extra. The
``tree_sitter`` and ``tree_sitter_css`` imports are wrapped in a
try/except so that importing ``genro_builders.contrib.css`` does not
force the heavy dependency on every user — only callers that invoke
the reverse API pay the cost.
"""

from __future__ import annotations

from typing import Any

try:
    import tree_sitter_css
    from tree_sitter import Language, Parser
except ImportError as exc:  # pragma: no cover - exercised only when extra missing
    _IMPORT_ERROR: ImportError | None = exc
    Language = None  # type: ignore[assignment,misc]
    Parser = None  # type: ignore[assignment,misc]
    tree_sitter_css = None  # type: ignore[assignment]
else:
    _IMPORT_ERROR = None

_INSTALL_HINT = (
    "Install the reverse extra: pip install 'genro-builders[reverse]'"
)

_PARSER: Any = None


def _get_parser() -> Any:
    """Return a lazily-built singleton ``tree_sitter.Parser`` for CSS."""
    global _PARSER
    if _IMPORT_ERROR is not None:
        raise ImportError(
            f"genro_builders.contrib.css reverse requires tree-sitter-css. "
            f"{_INSTALL_HINT}",
        ) from _IMPORT_ERROR
    if _PARSER is None:
        lang = Language(tree_sitter_css.language())  # type: ignore[misc]
        _PARSER = Parser(lang)  # type: ignore[misc]
    return _PARSER


def _parse_css(source: str) -> Any:
    """Parse a CSS source string and return the tree-sitter root node."""
    parser = _get_parser()
    tree = parser.parse(source.encode("utf-8"))
    return tree.root_node
