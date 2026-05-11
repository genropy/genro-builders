# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""End-to-end tests for HtmlBuilder + HtmlBuilderHandler."""

from __future__ import annotations

import io

import pytest

from genro_builders.contrib.html import HtmlBuilder, HtmlBuilderHandler


def _render(main_fn):
    """Helper: build a handler with the given main and return its render output."""

    class _Page(HtmlBuilderHandler):
        def main(self, root):
            main_fn(root)

    page = _Page()
    page.create()
    page.build()
    return page, page.render()


def test_html_render_default_mode_is_html():
    assert HtmlBuilder._default_render_mode == "html"


def test_html_render_simple_div():
    _, out = _render(lambda root: root.div("aaa"))
    assert out == "<div>aaa</div>"


def test_html_render_void_tag_self_closes():
    def build(root):
        body = root.body()
        body.img(src="logo.png")

    _, out = _render(build)
    assert out == '<body><img src="logo.png"/></body>'


def test_html_render_xml_false_emits_idiomatic_html5():
    class _Page(HtmlBuilderHandler):
        def main(self, root):
            body = root.body()
            body.img(src="logo.png")

    page = _Page()
    page.create()
    page.build()
    assert page.render(xml=False) == '<body><img src="logo.png"></body>'


def test_html_render_xml_true_default_matches_explicit():
    class _Page(HtmlBuilderHandler):
        def main(self, root):
            body = root.body()
            body.img(src="logo.png")

    page = _Page()
    page.create()
    page.build()
    assert page.render() == page.render(xml=True)


def test_html_render_unknown_kwarg_is_silently_ignored():
    """Decision 6: unknown kwargs are filtered, not raised."""

    class _Page(HtmlBuilderHandler):
        def main(self, root):
            root.div("x")

    page = _Page()
    page.create()
    page.build()
    # ``pretty`` is not a render_html parameter — must be ignored.
    assert page.render(pretty=True) == "<div>x</div>"


def test_html_render_attributes_keyword_collision():
    _, out = _render(lambda root: root.div("x", _class="foo"))
    assert out == '<div class="foo">x</div>'


def test_html_render_three_state_bool_true():
    def build(root):
        body = root.body()
        body.input(disabled=True)

    _, out = _render(build)
    assert out == '<body><input disabled="true"/></body>'


def test_html_render_three_state_bool_false():
    def build(root):
        body = root.body()
        body.input(disabled=False)

    _, out = _render(build)
    assert out == '<body><input disabled="false"/></body>'


def test_html_render_three_state_bool_none_currently_omitted():
    # ``None`` is currently filtered upstream (by Bag.set_item / the
    # grammar dispatch), so the renderer never sees the attribute.
    # The plan flags the "emit as null" semantics as a future
    # refinement that would require changing the upstream filter.
    def build(root):
        body = root.body()
        body.input(disabled=None)

    _, out = _render(build)
    assert out == "<body><input/></body>"


def test_html_render_text_escape():
    _, out = _render(lambda root: root.div("a & b < c > d"))
    assert out == "<div>a &amp; b &lt; c &gt; d</div>"


def test_html_render_attribute_quote_escape():
    _, out = _render(lambda root: root.div("x", _class='he said "hi"'))
    assert out == '<div class="he said &quot;hi&quot;">x</div>'


def test_html_render_nested():
    def build(root):
        d = root.div(_class="x")
        d.span("y")

    _, out = _render(build)
    assert out == '<div class="x"><span>y</span></div>'


def test_html_render_returns_string_when_target_is_none():
    _, out = _render(lambda root: root.div("a"))
    assert isinstance(out, str)


def test_html_render_target_writes_to_writable():
    class _Page(HtmlBuilderHandler):
        def main(self, root):
            root.div("a")

    page = _Page()
    page.create()
    page.build()
    buf = io.StringIO()
    page.render_target = buf
    result = page.render()
    assert result is None
    assert buf.getvalue() == "<div>a</div>"


def test_html_render_target_invalid_object_raises_type_error():
    class _Page(HtmlBuilderHandler):
        def main(self, root):
            root.div("a")

    page = _Page()
    page.create()
    page.build()
    page.render_target = 42  # neither writable nor callable
    with pytest.raises(TypeError):
        page.render()
