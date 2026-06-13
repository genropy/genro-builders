# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Data-side presentation: the datum knows how to present itself.

A ``mask`` attribute on the data node wraps the rendered value
(legacy gnrformatter vocabulary: ``%s`` is the value). Presentation
only: a data-element's bindings receive the raw datum, and ``?attr``
reads stay raw.
"""
from __future__ import annotations

from genro_builders.builder import BuilderHandler, TargetWrapper, component
from genro_builders.contrib.html import HtmlBuilder


def _mounted(page_cls):
    page = page_cls(name="main")
    BuilderHandler().add_builder(page)
    return page


def test_mask_wraps_the_rendered_value():
    class Page(HtmlBuilder):
        def main(self, root) -> None:
            body = root.body()
            body.dataSetter("temperatura", 38.5, mask="%s°")
            body.div("^temperatura")

    out = _mounted(Page).render(target=False)
    assert "<div>38.5°</div>" in out


def test_mask_applies_to_attribute_pointers_too():
    class Page(HtmlBuilder):
        def main(self, root) -> None:
            body = root.body()
            body.dataSetter("larghezza", 120, mask="%spx")
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
            body.dataSetter("temp", 10, mask="%s°")
            body.dataFormula("doppio", "doubled", t="^temp", _on_start=True)
            body.div("^doppio")

    out = _mounted(Page).render(target=False)
    # the formula got 10 (int), not "10°": 10*2 = 20, not "10°10°"
    assert "<div>20</div>" in out


def test_mask_composes_with_recipe_templates():
    class Page(HtmlBuilder):
        def main(self, root) -> None:
            body = root.body()
            body.dataSetter("prezzo", 99, mask="€ %s")
            body.div("x", p="^prezzo", title="costa ${p}")

    out = _mounted(Page).render(target=False)
    assert 'title="costa € 99"' in out


def test_wdg_attributes_travel_with_the_datum_and_win():
    class Page(HtmlBuilder):
        def main(self, root) -> None:
            body = root.body()
            body.dataSetter(
                "temperatura", 39.2, mask="%s°",
                _wdg={"color": "red", "font_weight": "bold"},
            )
            # the recipe says blue; the datum carries the exception: red wins
            body.div("^temperatura", color="blue")

    out = _mounted(Page).render(target=False)
    assert (
        '<div style="color: red; font-weight: bold">39.2°</div>' in out
    )


def test_mask_formats_fixed_decimals():
    class Page(HtmlBuilder):
        def main(self, root) -> None:
            body = root.body()
            body.dataSetter("prezzo", 45.0, mask="%.2f")
            body.dataSetter("sconto", 7, mask="€ %.2f")
            body.div("^prezzo")
            body.div("^sconto")

    out = _mounted(Page).render(target=False)
    assert "<div>45.00</div>" in out
    assert "<div>€ 7.00</div>" in out


def test_cell_patches_present_like_the_render():
    class Probe(TargetWrapper):
        accepts_partial = True
        render_opts = {"include_datapath": True}

        def __init__(self):
            self.batches = []

        def full(self, document):
            self.full_html = document

        def partial(self, patches):
            self.batches.append(patches)

    class Page(HtmlBuilder):
        @component
        def orderRow(self, root, node_label=None):
            row = root.div(datapath="." + node_label)
            row.input(value="^.qty", dtype="L")
            row.span("^.total")
            row.dataFormula(destination=".total", func="row_total",
                             qty="^.qty", price="^.price")

        def setup(self, data):
            data.set_item("rows.r1.qty", 2)
            data.set_item("rows.r1.price", 5.0)
            data.set_item("rows.r1.total", 10.0, mask="%.2f")

        def main(self, root):
            root.body().orderRow(iterate="^rows", id="rows_block")

        @staticmethod
        def row_total(qty, price):
            return round(float(qty) * float(price), 2)

    page = Page(name="main")
    probe = Probe()
    page.set_render_target(probe)
    handler = BuilderHandler(application=object())
    handler.add_builder(page)
    handler.activate()
    assert ">10.00</span>" in probe.full_html
    with handler.live():
        handler.data.set_item("main.rows.r1.qty", 3)
    # total -> 15.0; the value-only TEXT op must ship the MASKED value
    # ("15.00"): the cell lane presents exactly like the render does.
    texts = [p for batch in probe.batches for p in batch
             if p.get("op") == "text"]
    assert texts and texts[-1]["value"] == "15.00"


def test_wdg_does_not_travel_on_attribute_pointers():
    class Page(HtmlBuilder):
        def main(self, root) -> None:
            body = root.body()
            body.dataSetter("temp", 10, _wdg={"color": "red"})
            body.div("x", title="^temp")

    out = _mounted(Page).render(target=False)
    assert 'title="10"' in out
    assert "color" not in out
