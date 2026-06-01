# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for the three data-elements (data, data_formula, data_controller).

First block: NON reactive. Only the create() data-pass driven by
``data_elements()``, run once before the first render (after pointer
registration, before subscribes are armed).

Semantics under test (the triangle case):
    - ``data`` always writes its seed value at create.
    - ``data_formula`` / ``data_controller`` execute at start ONLY when
      ``_on_start=True``; otherwise they stay dormant (will react later,
      in the reactive block — out of scope here).

Data-elements are declared via the canonical builder API inside
``main(self, root)`` and are transparent to the renderer (emit no markup).
"""
from __future__ import annotations

from genro_builders.contrib.html import HtmlBuilderHandler


def _calc_area(base, altezza):
    return base * altezza / 2


# ---------------------------------------------------------------------------
# data — always written at create
# ---------------------------------------------------------------------------


def test_data_writes_seed_values():
    """Plain ``data`` leaves write their value into the data bag at create."""

    class P(HtmlBuilderHandler):
        def main(self, root) -> None:
            body = root.body(datapath="tri")
            body.data(".altezza", 6)
            body.data(".base", 10)

    page = P()
    page.create()
    assert page.data.get_item("tri.altezza") == 6
    assert page.data.get_item("tri.base") == 10


# ---------------------------------------------------------------------------
# data_formula — _on_start governs execution at create
# ---------------------------------------------------------------------------


def test_formula_not_computed_without_on_start():
    """A formula without ``_on_start`` does NOT run at create: area is absent."""

    class P(HtmlBuilderHandler):
        def main(self, root) -> None:
            body = root.body(datapath="tri")
            body.data(".altezza", 6)
            body.data(".base", 10)
            body.data_formula(
                ".area", _calc_area, base="^.base", altezza="^.altezza",
            )

    page = P()
    page.create()
    assert page.data.get_item("tri.base") == 10
    assert page.data.get_item("tri.altezza") == 6
    # the formula did not run: area is missing
    assert page.data.get_item("tri.area") is None


def test_formula_computed_with_on_start():
    """A formula with ``_on_start=True`` runs at create: area is computed."""

    class P(HtmlBuilderHandler):
        def main(self, root) -> None:
            body = root.body(datapath="tri")
            body.data(".altezza", 6)
            body.data(".base", 10)
            body.data_formula(
                ".area", _calc_area, base="^.base", altezza="^.altezza",
                _on_start=True,
            )

    page = P()
    page.create()
    assert page.data.get_item("tri.area") == 30


# ---------------------------------------------------------------------------
# func by name (handler method) — same result as the callable form
# ---------------------------------------------------------------------------


def test_formula_func_by_name():
    """``func`` given as a handler-method name resolves and computes."""

    class P(HtmlBuilderHandler):
        def calc_area(self, base, altezza):
            return base * altezza / 2

        def main(self, root) -> None:
            body = root.body(datapath="tri")
            body.data(".altezza", 6)
            body.data(".base", 10)
            body.data_formula(
                ".area", "calc_area", base="^.base", altezza="^.altezza",
                _on_start=True,
            )

    page = P()
    page.create()
    assert page.data.get_item("tri.area") == 30


# ---------------------------------------------------------------------------
# transparency — data-elements emit no markup
# ---------------------------------------------------------------------------


def test_data_elements_are_transparent_to_render():
    """Data-elements produce no markup in the rendered HTML."""

    class P(HtmlBuilderHandler):
        def main(self, root) -> None:
            body = root.body(datapath="tri")
            body.data(".base", 10)
            body.data(".altezza", 6)
            body.data_formula(
                ".area", _calc_area, base="^.base", altezza="^.altezza",
                _on_start=True,
            )

    page = P()
    page.create()
    html = page.render()
    assert "data_formula" not in html
    assert "<data" not in html
    assert "area" not in html
