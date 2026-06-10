# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Data-side presentation: the datum knows how to present itself.

A ``mask`` attribute on the data node wraps the rendered value
(legacy gnrformatter vocabulary: ``%s`` is the value). Presentation
only: a data-element's bindings receive the raw datum, and ``?attr``
reads stay raw.
"""
from __future__ import annotations

from genro_builders.builder import BuilderHandler
from genro_builders.contrib.html import HtmlBuilder


def _mounted(page_cls):
    page = page_cls(name="main")
    BuilderHandler().add_builder(page)
    return page


def test_mask_wraps_the_rendered_value():
    class Page(HtmlBuilder):
        def main(self, root) -> None:
            body = root.body()
            body.data_setter("temperatura", 38.5, mask="%s°")
            body.div("^temperatura")

    out = _mounted(Page).render(target=False)
    assert "<div>38.5°</div>" in out


def test_mask_applies_to_attribute_pointers_too():
    class Page(HtmlBuilder):
        def main(self, root) -> None:
            body = root.body()
            body.data_setter("larghezza", 120, mask="%spx")
            body.div("x", title="^larghezza")

    out = _mounted(Page).render(target=False)
    assert 'title="120px"' in out


def test_formula_bindings_receive_the_raw_datum():
    class Page(HtmlBuilder):
        @staticmethod
        def doubled(t):
            return t * 2

        def main(self, root) -> None:
            body = root.body()
            body.data_setter("temp", 10, mask="%s°")
            body.data_formula("doppio", "doubled", t="^temp", _on_start=True)
            body.div("^doppio")

    out = _mounted(Page).render(target=False)
    # the formula got 10 (int), not "10°": 10*2 = 20, not "10°10°"
    assert "<div>20</div>" in out


def test_mask_composes_with_recipe_templates():
    class Page(HtmlBuilder):
        def main(self, root) -> None:
            body = root.body()
            body.data_setter("prezzo", 99, mask="€ %s")
            body.div("x", p="^prezzo", title="costa ${p}")

    out = _mounted(Page).render(target=False)
    assert 'title="costa € 99"' in out


def test_wdg_attributes_travel_with_the_datum_and_win():
    class Page(HtmlBuilder):
        def main(self, root) -> None:
            body = root.body()
            body.data_setter(
                "temperatura", 39.2, mask="%s°",
                _wdg={"color": "red", "font_weight": "bold"},
            )
            # the recipe says blue; the datum carries the exception: red wins
            body.div("^temperatura", color="blue")

    out = _mounted(Page).render(target=False)
    assert (
        '<div style="color: red; font-weight: bold">39.2°</div>' in out
    )


def test_wdg_does_not_travel_on_attribute_pointers():
    class Page(HtmlBuilder):
        def main(self, root) -> None:
            body = root.body()
            body.data_setter("temp", 10, _wdg={"color": "red"})
            body.div("x", title="^temp")

    out = _mounted(Page).render(target=False)
    assert 'title="10"' in out
    assert "color" not in out
