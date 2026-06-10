# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Template inputs: an attribute referenced by a ``${...}`` template of
the same node is consumed by the expansion and is not emitted.

The name is free — it is the usage, visible in the recipe, that marks
the attribute as a template input. Canonical idiom: a computed datum
composed with an authored unit (``w="^mywidth", width="${w}px"``).
"""
from __future__ import annotations

from genro_builders.builder import BuilderHandler
from genro_builders.contrib.html import HtmlBuilder


def _render(main_fn):
    class Page(HtmlBuilder):
        def main(self, root) -> None:
            main_fn(root)

    page = Page(name="main")
    BuilderHandler().add_builder(page)
    return page.render(target=False)


def test_template_input_is_consumed_not_emitted():
    def main(root):
        body = root.body()
        body.data_setter("mywidth", 120)
        body.div("testo", w="^mywidth", width="${w}px")

    out = _render(main)
    assert '<div style="width: 120px">testo</div>' in out
    assert "w=" not in out


def test_dual_use_goes_through_a_template_itself():
    def main(root):
        root.div("x", t="hello", title="${t}", aria_label="${t} world")

    out = _render(main)
    assert 'title="hello"' in out
    assert 'aria-label="hello world"' in out or 'aria_label="hello world"' in out
    assert " t=" not in out


def test_value_template_consumes_its_inputs():
    def main(root):
        body = root.body()
        body.data_setter("nome", "Mario")
        body.div("Ciao ${n}", n="^nome")

    out = _render(main)
    assert "<div>Ciao Mario</div>" in out
    assert "n=" not in out
