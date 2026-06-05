# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""XSLT-to-Python transpiler.

Reads an ``.xslt`` stylesheet and emits Python source that rebuilds it
with :class:`XsltBuilder`. The pipeline is two trees with a walk in
between::

    .xslt --lxml.parse--> XML tree --walk--> Python AST --ast.unparse--> .py

This is **phase 1**: a faithful, verbose transpiler — one variable per
element with children, instructions and literal result elements emitted
as-is. It is deliberately unclever so the round-trip (xslt -> py ->
execute -> render) can be checked against the original. Readability
passes (fluent chaining, variable reuse, semantic names) are a separate
phase 2 over the AST, not done here.

The transpiler is **agnostic**: it knows XSLT (instructions keyed by the
``http://www.w3.org/1999/XSL/Transform`` namespace URI, not the prefix)
and copies everything else verbatim as a literal result element. It does
not know about local conventions such as ``@@placeholder@@`` — those are
plain string content.
"""

from __future__ import annotations

from .backend import XsltTranspiler

__all__ = ["XsltTranspiler"]
