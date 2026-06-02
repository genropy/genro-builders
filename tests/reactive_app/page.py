# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""TrianglePage — an HtmlBuilderHandler with a reactive area formula.

Data model under ``tri``: ``base`` and ``altezza`` are seeded by
``data_setter``; ``area`` is a ``data_formula`` that reads them through
``^`` pointers and writes ``base*altezza/2`` whenever a dependency changes.
The formula ``func`` is resolved by name over :class:`DataLogic`, wired in
through ``_build_data_logic``.

The handler carries ``self.application`` (dual relationship): the app
creates it passing itself in. A handler without an application is a plain
sync handler; this one is reactive because it has one.
"""

from __future__ import annotations

from genro_builders.contrib.html import HtmlBuilderHandler

from .logic import DataLogic


class TrianglePage(HtmlBuilderHandler):
    """Triangle page: base + altezza -> reactive area."""

    def _build_data_logic(self) -> list[object]:
        """Resolve data-element funcs over DataLogic (then self)."""
        return [DataLogic(), self]

    def main(self, root) -> None:
        body = root.body(datapath="tri")
        body.data_setter(".base", 10)
        body.data_setter(".altezza", 6)
        body.data_formula(
            ".area", "calc_area", base="^.base", altezza="^.altezza",
        )
        body.h1("^.area", node_id="area")
