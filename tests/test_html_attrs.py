# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""HTML attribute serialization: every value is escaped at the
embedding point (``_format_attrs``), the composed ``style`` included.

A double quote inside a CSS value (font names, ``content``) is valid
CSS; unescaped it would close the ``style`` attribute and spill the
rest as garbage attributes — markup breakage, and an injection point
when the value comes from data.
"""
from __future__ import annotations

from genro_builders.contrib.html import HtmlBuilder


def _render(main_fn):
    class Page(HtmlBuilder):
        def main(self, root) -> None:
            main_fn(root)

    page = Page()
    page.create()
    return page.render(target=False)


def test_style_value_is_escaped():
    out = _render(
        lambda root: root.div("x", font_family='"Helvetica Neue", sans-serif'),
    )
    assert (
        'style="font-family: &quot;Helvetica Neue&quot;, sans-serif"' in out
    )


def test_regular_attr_value_is_escaped():
    out = _render(lambda root: root.div("x", title='a "b" & c'))
    assert 'title="a &quot;b&quot; &amp; c"' in out


def test_boolean_attr_true_emits_bare_presence():
    out = _render(lambda root: root.input(disabled=True, html_type="text"))
    assert "<input disabled" in out
    assert 'disabled="' not in out


def test_boolean_attr_false_emits_nothing():
    out = _render(lambda root: root.input(disabled=False, html_type="text"))
    assert "disabled" not in out


def test_boolean_attr_reactive_pointer_decides_presence():

    class Page(HtmlBuilder):
        def main(self, root) -> None:
            body = root.body()
            body.dataSetter("locked", False)
            body.input(disabled="^locked", html_type="text")

    page = Page(name="main")
    page.create()
    assert "disabled" not in page.render(target=False)
    # Re-render is the update model: change the datum, render again.
    page.data.set_item("locked", True)
    assert "<input disabled" in page.render(target=False)


def test_non_native_flags_keep_js_literals():
    out = _render(lambda root: root.div("x", data_loaded=False))
    assert 'data_loaded="false"' in out
