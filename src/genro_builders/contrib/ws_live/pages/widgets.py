# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Widgets page: the component collection, live and TYPED.

Every field is a ``labeled_field`` from ``HtmlComponentsBase``; each
widget declares its dtype, so the datastore holds DATA, not text: the
birth date is a ``date`` (the age formula does date arithmetic on it),
weight and height are numbers (the BMI formula divides them). Edit
anything: the typed mutation travels, the formulas recompute, the
summary re-renders — pushed back over the connection.
"""

from __future__ import annotations

import datetime

from genro_builders.contrib.html import HtmlComponentsBase

from ..base_page import WsLivePage

PAGE_TITLE = "Widgets (typed collection)"


class Page(WsLivePage, HtmlComponentsBase):
    """A profile form: typed widgets feeding live formulas."""

    @staticmethod
    def age_from_born(born):
        if born is None:
            return None
        today = datetime.date.today()
        before_birthday = (today.month, today.day) < (born.month, born.day)
        return today.year - born.year - before_birthday

    @staticmethod
    def body_mass_index(weight, height):
        if not weight or not height:
            return None
        return round(float(weight) / (height / 100) ** 2, 1)

    def setup(self, data):
        self.set_data("person.name", "Mario Rossi")
        self.set_data("person.born", datetime.date(1980, 5, 12))
        self.set_data("person.weight", 82.5)
        self.set_data("person.height", 178)
        self.set_data("person.color", "#3498db")

    def main(self, root):
        pane = root.div(datapath="person", max_width="420px",
                        display="flex", flex_direction="column", gap="8px")
        pane.h1("Profile")
        pane.labeled_field(label="Name", kind="textbox", value="^.name",
                           border=True, rounded=True)
        # dtype D: the datastore holds a date object — the age formula
        # SUBTRACTS dates (a string would crash it).
        pane.labeled_field(label="Born", kind="datepicker", value="^.born",
                           border=True, rounded=True, label_position="left")
        pane.labeled_field(label="Weight (kg)", dtype="N", places=1,
                           value="^.weight", border=True, rounded=True,
                           label_position="left", min="0", max="300")
        pane.labeled_field(label="Height (cm)", dtype="L",
                           value="^.height", border=True, rounded=True,
                           label_position="left", min="0", max="250")
        pane.labeled_field(label="Favorite color", kind="colorpicker",
                           value="^.color", border=False)
        # Derived data: age from the birth date, BMI from weight/height.
        pane.data_formula(destination=".age", func="age_from_born",
                          born="^.born", _on_start=True)
        pane.data_formula(destination=".bmi", func="body_mass_index",
                          weight="^.weight", height="^.height",
                          _on_start=True)
        summary = pane.p(style_border_left="^.color",
                         border_left_width="4px",
                         border_left_style="solid", padding_left="8px")
        summary.span("${name}, ${age} years — BMI ${bmi}",
                     name="^.name", age="^.age", bmi="^.bmi")
