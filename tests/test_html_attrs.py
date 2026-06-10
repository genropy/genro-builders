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
