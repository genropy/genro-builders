# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""04 — Data-elements at create time. See README.md for the walkthrough."""
from __future__ import annotations

from pathlib import Path

from genro_builders.contrib.html import HtmlBuilderHandler


class Section1(HtmlBuilderHandler):
    """data_setter — seed values, always available at create."""

    def main(self, root):
        body = root.body(datapath="invoice")
        body.data_setter(".amount", 1000)
        body.data_setter(".currency", "EUR")
        body.h2("Seeded values")
        body.p("Amount: ").span("^.amount")
        body.p("Currency: ").span("^.currency")


class Section2(HtmlBuilderHandler):
    """data_formula with _on_start — a derived value computed at create."""

    @staticmethod
    def calc_vat_total(net, rate):
        return round(net * (1 + rate), 2)

    def main(self, root):
        body = root.body(datapath="invoice")
        body.data_setter(".net", 1000)
        body.data_setter(".rate", 0.22)
        body.data_formula(
            ".total", "calc_vat_total", net="^.net", rate="^.rate",
            _on_start=True,
        )
        body.h2("Net + VAT")
        body.p("Net: ").span("^.net")
        body.p("Gross (with VAT): ").span("^.total")


class Section3(HtmlBuilderHandler):
    """data_controller with _on_start — a side-effect step writing the bag."""

    @staticmethod
    def build_label(node, count):
        word = "item" if count == 1 else "items"
        node.set_relative_data(".label", f"{count} {word}")

    def main(self, root):
        body = root.body(datapath="cart")
        body.data_setter(".count", 3)
        body.data_controller("build_label", count="^.count", _on_start=True)
        body.h2("Cart")
        body.p("Summary: ").span("^.label")


class Section4(HtmlBuilderHandler):
    """Dormant formula — without _on_start it produces nothing at create."""

    @staticmethod
    def calc_vat_total(net, rate):
        return round(net * (1 + rate), 2)

    def main(self, root):
        body = root.body(datapath="invoice")
        body.data_setter(".net", 1000)
        body.data_setter(".rate", 0.22)
        body.data_formula(
            ".total", "calc_vat_total", net="^.net", rate="^.rate",
        )
        body.h2("Dormant formula")
        body.p("Net: ").span("^.net")
        body.p("Gross (empty — formula dormant): ").span("^.total")


def _render_section(handler_cls, *, pretty=True):
    page = handler_cls()
    page.create()
    return page.render(pretty=pretty)


if __name__ == "__main__":
    sections = [Section1, Section2, Section3, Section4]
    parts = []
    for i, cls in enumerate(sections, 1):
        parts.append(f"<!-- Section {i} -->")
        parts.append(_render_section(cls))
        parts.append("")
    rendered = "\n".join(parts)

    output = Path(__file__).with_suffix(".html")
    output.write_text(rendered)
    print(rendered)
    print(f"Saved to {output}")
