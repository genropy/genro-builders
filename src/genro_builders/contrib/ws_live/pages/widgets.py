# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Widgets page: the component collection, live.

Every field is a ``labeled_field`` from ``HtmlComponentsBase``: the
value pointer passes through to the inner input (CMP.4), so each
widget displays its datum AND carries the write-back address. Edit
anything: the mutation travels, the summary line re-renders — pushed
back over the connection.
"""

from __future__ import annotations

from genro_builders.contrib.html import HtmlComponentsBase

from ..base_page import WsLivePage

PAGE_TITLE = "Widgets (the collection)"


class Page(WsLivePage, HtmlComponentsBase):
    """A profile form built only with collection widgets."""

    @staticmethod
    def double_age(age):
        return None if age is None else age * 2

    def setup(self, data):
        self.set_data("person.name", "Mario Rossi")
        self.set_data("person.born", "1980-05-12")
        self.set_data("person.age", 45)
        self.set_data("person.color", "#3498db")
        self.set_data("person.newsletter", True)

    def main(self, root):
        pane = root.div(datapath="person", max_width="420px",
                        display="flex", flex_direction="column", gap="8px")
        pane.h1("Profile")
        pane.labeled_field(label="Name", kind="textbox", value="^.name",
                           border=True, rounded=True)
        pane.labeled_field(label="Born", kind="datepicker", value="^.born",
                           border=True, rounded=True, label_position="left")
        # dtype="L": the client sends value+dtype, the server types the
        # write — the datastore holds an int. The formula is the living
        # proof: 45 -> 90 (an untyped "45" would double to "4545").
        pane.labeled_field(label="Age", lbl=None, dtype="L", value="^.age",
                           border=True, rounded=True, label_position="left",
                           min="0", max="120")
        pane.data_formula(destination=".age_twice", func="double_age",
                          age="^.age", _on_start=True)
        pane.labeled_field(label="Favorite color", kind="colorpicker",
                           value="^.color", border=False)
        pane.labeled_field(label="Newsletter", kind="checkbox",
                           value="^.newsletter", border=False,
                           label_position="left")
        summary = pane.p(style_border_left="^.color",
                         border_left_width="4px",
                         border_left_style="solid", padding_left="8px")
        summary.span("${name} — born ${born} — age ×2 = ${twice}",
                     name="^.name", born="^.born", twice="^.age_twice")
