# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""12 — Widget components: the first collection. See readme.md.

``HtmlComponentsBase`` brings the input widgets (named after the
WIDGET, legacy flavor) and ``labeled_field``. A reactive ``value``
pointer passes through to the inner input (CMP.4), so in the reactive
render the widget displays AND carries its write-back address.
"""
from __future__ import annotations

from genro_builders.builder import BuilderHandler
from genro_builders.contrib.html import HtmlBuilder, HtmlComponentsBase


class CustomPage(HtmlBuilder, HtmlComponentsBase):
    def setup(self, data):
        data.set_item("person.name", "Mario Rossi")
        data.set_item("person.born", "1980-05-12")
        data.set_item("person.color", "#3498db")
        data.set_item("person.age", 45)
        data.set_item("person.newsletter", True)

    def main(self, root):
        body = root.body(datapath="person")
        body.h2("Profile")
        # labeled_field: label + widget in one box. The four corners:
        body.labeled_field(label="Name", kind="textbox", value="^.name",
                           border=True, rounded=True)
        body.labeled_field(label="Born", kind="datepicker", value="^.born",
                           border=True, label_position="left")
        body.labeled_field(label="Favorite color", kind="colorpicker",
                           value="^.color", border=False)
        body.labeled_field(label="Age", kind="numberbox", value="^.age",
                           border=False, label_position="left",
                           min="0", max="120")
        # Bare widgets compose like any element:
        row = body.div(display="flex", gap="8px", align_items="center")
        row.slider(value="^.age", min="0", max="120")
        row.checkbox(value="^.newsletter")


if __name__ == "__main__":
    page = CustomPage()
    handler = BuilderHandler()
    handler.add_builder(page)
    page.set_render_target("output.html")
    page.render(pretty=True)
    print(page.rendered_target)
