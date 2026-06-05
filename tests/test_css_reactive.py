# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""CSS on the canonical walk: pointer resolution + class_ keyword form.

These exercise the behaviour the CssRenderer gains once it rides the
universal walk (``runtime_values``) instead of reading ``node.attr``
raw: rule values that are pointers (``^``/``=``) resolve against the
handler data, and the canonical ``class_`` keyword form is accepted in
selectors (like html/svg).
"""
from __future__ import annotations

from genro_builders.contrib.css import CssBuilderHandler


def test_rule_value_pointer_is_resolved():
    """A rule property whose value is a pointer resolves from data."""

    class _Page(CssBuilderHandler):
        def setup(self):
            self.data.set_item("theme.accent", "#ff0066")

        def main(self, root):
            root.selector(class_="card").rule(color="^theme.accent")

    page = _Page()
    page.create()
    out = page.render()
    assert "color: #ff0066;" in out
    assert "^" not in out


def test_selector_accepts_class_suffix_form():
    """The canonical ``class_`` keyword form yields a class selector."""

    class _Page(CssBuilderHandler):
        def main(self, root):
            root.selector(class_="card").rule(color="red")

    page = _Page()
    page.create()
    out = page.render()
    assert out == ".card {\n  color: red;\n}\n"
