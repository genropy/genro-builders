# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Data-element func resolution over the ``data_logic`` sources (DAT.4).

A data-element ``func`` is a ``@staticmethod`` resolved by NAME, not a
callable passed in: the recipe names it, the builder resolves it. The
sources are ``data_logic``, whose default is ``[self]`` — the builder owns
its logic. ``_build_data_logic`` is the override point that adds sources,
searched left-to-right, first-wins.

Resolution is static (``inspect.getattr_static``) and errors are explicit:
a source owning the name but not as a staticmethod raises TypeError; a
miss on every source raises AttributeError naming the sources tried.

Every data-element computes at ``create()``, once, in document order: the
formulas here need no flag to run.
"""
from __future__ import annotations

import pytest

from genro_builders.contrib.html import HtmlBuilder


class Geometry:
    """An external logic source: the functions live outside the builder."""

    @staticmethod
    def calc_area(base: float, height: float) -> float:
        return base * height / 2


class AreaPage(HtmlBuilder):
    """``area`` computed at start from ``base`` and ``height``."""

    def main(self, root) -> None:
        body = root.body()
        body.dataSetter("base", 10)
        body.dataSetter("height", 6)
        body.dataFormula(
            destination="area", func="calc_area",
            base="^base", height="^height",
        )


def _mount(page_cls):
    page = page_cls(name="main")
    page.create()
    return page


def test_default_source_is_the_builder_itself():
    class Page(AreaPage):
        @staticmethod
        def calc_area(base, height):
            return base * height / 2

    page = _mount(Page)
    assert page.data_logic == [page]
    assert page.data.get_item("area") == 30


def test_build_data_logic_adds_an_external_source():
    class Page(AreaPage):
        def _build_data_logic(self):
            return [Geometry(), self]

    page = _mount(Page)
    assert [type(s).__name__ for s in page.data_logic] == ["Geometry", "Page"]
    assert page.data.get_item("area") == 30


def test_first_source_wins_over_the_later_ones():
    class Page(AreaPage):
        @staticmethod
        def calc_area(base, height):
            return -1                     # never reached: Geometry is first

        def _build_data_logic(self):
            return [Geometry(), self]

    page = _mount(Page)
    assert page.data.get_item("area") == 30


def test_a_single_source_is_accepted_not_only_a_list():
    class Page(AreaPage):
        def _build_data_logic(self):
            return Geometry()             # bare, not wrapped in a list

    page = _mount(Page)
    assert [type(s).__name__ for s in page.data_logic] == ["Geometry"]
    assert page.data.get_item("area") == 30


def test_a_func_that_is_not_a_staticmethod_raises():
    class Page(AreaPage):
        def calc_area(self, base, height):
            return base * height / 2

    with pytest.raises(TypeError, match="must be a @staticmethod"):
        _mount(Page)


def test_an_unknown_func_raises_naming_the_sources():
    class Page(AreaPage):
        def _build_data_logic(self):
            return [Geometry(), self]

        def main(self, root) -> None:
            root.body().dataFormula(
                destination="area", func="calc_perimeter",
                base="^base",
            )

    with pytest.raises(AttributeError, match="Geometry, Page"):
        _mount(Page)
