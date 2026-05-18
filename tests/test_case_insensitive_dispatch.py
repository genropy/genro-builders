# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Case insensitivity unificata sul dispatch dei tag della grammar.

Regola: lookup case-insensitive (underscore-sensitive). Wire format
mantiene la case originale del decoratore. Kwargs restano
case-sensitive. Collisione lowercase tra decoratori → ValueError al
class build.
"""
from __future__ import annotations

import pytest

from genro_builders.builder import BagBuilderBase, element
from genro_builders.contrib.html import HtmlBuilderHandler
from genro_builders.contrib.svg import SvgBuilderHandler


class _HtmlPage(HtmlBuilderHandler):
    def main(self, root):
        pass


class _SvgPage(SvgBuilderHandler):
    def main(self, root):
        pass


def test_html_div_exact_case():
    page = _HtmlPage()
    page.create()
    page.source.body().div(_class="x")
    assert '<div class="x"' in page.render()


def test_html_div_uppercase():
    page = _HtmlPage()
    page.create()
    page.source.body().Div(_class="x")
    assert '<div class="x"' in page.render()


def test_html_div_mixed_case():
    page = _HtmlPage()
    page.create()
    page.source.body().DIV(_class="x")
    assert '<div class="x"' in page.render()


def test_svg_linear_gradient_exact_case():
    page = _SvgPage()
    page.create()
    page.source.svg().defs().linearGradient(id="g1")
    out = page.render()
    assert "<linearGradient" in out
    assert "<lineargradient" not in out


def test_svg_linear_gradient_lowercase():
    """Wire format keeps the ORIGINAL case decorated on the builder."""
    page = _SvgPage()
    page.create()
    page.source.svg().defs().lineargradient(id="g1")
    out = page.render()
    assert "<linearGradient" in out
    assert "<lineargradient" not in out


def test_svg_underscore_does_not_match():
    """Underscore is significant: `linear_gradient` is a different name."""
    page = _SvgPage()
    page.create()
    svg = page.source.svg()
    with pytest.raises(AttributeError):
        svg.defs().linear_gradient(id="g1")


def test_kwargs_remain_case_sensitive():
    """Tag dispatch is case-insensitive, kwargs are not.
    `id` and `ID` produce two distinct attributes in the output."""
    page = _HtmlPage()
    page.create()
    page.source.body().div(id="lowercase", ID="uppercase")
    out = page.render()
    assert 'id="lowercase"' in out
    assert 'ID="uppercase"' in out


def test_duplicate_tag_lowercase_collision_raises():
    """Two @element decorators differing only in case must raise at
    class construction time (in __init_subclass__)."""
    with pytest.raises(ValueError, match="(?i)duplicate|collision"):

        class _Colliding(BagBuilderBase):
            @element(sub_tags="")
            def widget(self): ...

            @element(sub_tags="")
            def Widget(self): ...


def test_dir_exposes_original_case_svg():
    """dir() on a node returns the original-case tag names (what the
    decorator declared), not all lowercased variants."""
    page = _SvgPage()
    page.create()
    defs = page.source.svg().defs()
    names = dir(defs)
    assert "linearGradient" in names
    assert "lineargradient" not in names


def test_dir_exposes_original_case_html():
    """Same check on HTML (where original case == lowercase)."""
    page = _HtmlPage()
    page.create()
    body = page.source.body()
    names = dir(body)
    assert "div" in names
    assert "p" in names
