# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Template inputs: an attribute referenced by a ``${...}`` template of
the same node is consumed by the expansion and is not emitted.

The name is free — it is the usage, visible in the recipe, that marks
the attribute as a template input. Canonical idiom: a computed datum
composed with an authored unit (``w="^mywidth", width="${w}px"``).
"""
from __future__ import annotations

import pytest

from genro_builders.contrib.html import HtmlBuilder


def _render(main_fn):
    class Page(HtmlBuilder):
        def main(self, root) -> None:
            main_fn(root)

    page = Page(name="main")
    page.create()
    return page.render(target=False)


def test_template_input_is_consumed_not_emitted():
    def main(root):
        body = root.body()
        body.dataSetter("mywidth", 120)
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


def test_value_is_literal_and_does_not_consume_attributes():
    def main(root):
        body = root.body()
        body.dataSetter("nome", "Mario")
        body.div("Ciao ${n}", n="^nome")

    out = _render(main)
    assert '<div n="Mario">Ciao ${n}</div>' in out
    assert 'n="Mario"' in out


def test_escaped_attribute_template_is_literal_and_does_not_consume():
    out = _render(lambda root: root.div(title=r"\${missing} ${name}", name="Mario"))
    assert 'title="${missing} Mario"' in out
    assert " name=" not in out


def test_raw_html_suffix_and_script_preserve_node_templates():
    def main(root):
        root.div("<b>${name}</b>::HTML")
        root.div("<b>${name}</b>")
        root.script('const text = `${name}`;')
    out = _render(main)
    assert "<div><b>${name}</b></div>" in out
    assert "<div>&lt;b&gt;${name}&lt;/b&gt;</div>" in out
    assert '<script>const text = `${name}`;</script>' in out
    assert "::HTML" not in out


def test_data_element_attributes_are_not_templates():
    class Page(HtmlBuilder):
        def main(self, root) -> None:
            body = root.body()
            body.dataSetter("total", 42)
            body.dataSetter("label", "${total}")
            body.dataFormula(
                destination="msg", func="echo",
                script="`Total: ${total}` ${stamp}", total="^total",
            )

        @staticmethod
        def echo(script, total):
            return f"{script}|{total}"

    page = Page(name="main")
    page.create()
    assert page.data.get_item("label") == "${total}"
    assert page.data.get_item("msg") == "`Total: ${total}` ${stamp}|42"


def test_missing_template_name_raises_the_js_message():
    with pytest.raises(ValueError, match="Unknown template parameter 'missing'"):
        _render(lambda root: root.div(title="${missing}"))
