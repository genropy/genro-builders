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
    return page, page.render()


def _render_pretty(main_fn):
    """Same as ``_render`` but with ``pretty=True``."""

    class _Page(HtmlBuilderHandler):
        def main(self, root):
            main_fn(root)

    page = _Page()
    page.create()
    return page, page.render(pretty=True)


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
    assert page.render(xml=False) == '<body><img src="logo.png"></body>'


def test_html_render_xml_true_default_matches_explicit():
    class _Page(HtmlBuilderHandler):
        def main(self, root):
            body = root.body()
            body.img(src="logo.png")

    page = _Page()
    page.create()
    assert page.render() == page.render(xml=True)


def test_html_render_unknown_kwarg_is_silently_ignored():
    """Decision 6: unknown kwargs are filtered, not raised."""

    class _Page(HtmlBuilderHandler):
        def main(self, root):
            root.div("x")

    page = _Page()
    page.create()
    # ``no_such_option`` is not a render_html parameter — must be ignored.
    assert page.render(no_such_option=True) == "<div>x</div>"


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


def test_html_render_style_content_not_escaped():
    """``<style>`` is a raw text element: CSS combinators survive verbatim."""
    _, out = _render(lambda root: root.style("h1 > span { color: red; }"))
    assert out == "<style>h1 > span { color: red; }</style>"


def test_html_render_script_content_not_escaped():
    """``<script>`` is a raw text element: JS operators survive verbatim."""
    _, out = _render(lambda root: root.script("if (a && b > c) { x(); }"))
    assert out == "<script>if (a && b > c) { x(); }</script>"


def test_html_render_attribute_quote_escape():
    _, out = _render(lambda root: root.div("x", _class='he said "hi"'))
    assert out == '<div class="he said &quot;hi&quot;">x</div>'


def test_html_render_dialect_escape_emits_literal_attribute():
    """``html_<x>`` emits the literal HTML attribute ``<x>``."""
    _, out = _render(lambda root: root.input(html_type="email"))
    assert out == '<input type="email"/>'


def test_html_render_dialect_escape_bypasses_css_root():
    """``html_width`` is the HTML attribute; bare ``width`` is still CSS."""
    _, attr = _render(lambda root: root.img(html_width=50))
    _, css = _render(lambda root: root.img(width=50))
    assert attr == '<img width="50"/>'
    assert css == '<img style="width: 50"/>'


def test_html_render_dialect_escape_value_is_escaped():
    """The escape acts on the name; the value still gets entity-escaped."""
    _, out = _render(lambda root: root.div("x", html_title="a & b"))
    assert out == '<div title="a &amp; b">x</div>'


class _BoundPage(HtmlBuilderHandler):
    def setup(self):
        self.data.set_item("states.NSW.name", "New South Wales")
        self.data.set_item("ui.theme", "dark")

    def main(self, root):
        row = root.body(datapath="states").div(datapath=".NSW")
        row.input(value="^.name", _class="=ui.theme")


def test_datapath_off_by_default():
    """No ``data-*-pointer`` unless include_datapath is requested."""
    page = _BoundPage()
    page.create()
    assert "data-" not in page.render()


def test_datapath_emits_absolute_path_for_each_pointer():
    """Each pointer attribute gets a data-<name>-pointer with its abs path."""
    page = _BoundPage()
    page.create()
    out = page.render(include_datapath=True)
    assert 'data-value-pointer="states.NSW.name"' in out
    assert 'data-class-pointer="ui.theme"' in out          # _class -> class
    assert 'value="New South Wales"' in out                # resolved value stays


def test_html_render_nested():
    def build(root):
        d = root.div(_class="x")
        d.span("y")

    _, out = _render(build)
    assert out == '<div class="x"><span>y</span></div>'


def test_html_render_pretty_text_only_stays_inline():
    """An element whose only child is text stays on one line."""
    _, out = _render_pretty(lambda root: root.div("Hello"))
    assert out == "<div>Hello</div>\n"


def test_html_render_pretty_nested_elements_indent_two_spaces():
    """Element children move to their own line with 2-space indent."""
    def build(root):
        body = root.body()
        body.h1("Hello")
        body.p("Paragraph.")

    _, out = _render_pretty(build)
    assert out == (
        "<body>\n"
        "  <h1>Hello</h1>\n"
        "  <p>Paragraph.</p>\n"
        "</body>\n"
    )


def test_html_render_pretty_void_tags_on_their_own_line():
    def build(root):
        body = root.body()
        body.img(src="logo.png")
        body.br()
        body.p("text")

    _, out = _render_pretty(build)
    assert out == (
        "<body>\n"
        '  <img src="logo.png"/>\n'
        "  <br/>\n"
        "  <p>text</p>\n"
        "</body>\n"
    )


def test_html_render_pretty_deep_nesting_indents_per_level():
    def build(root):
        body = root.body()
        div = body.div(_class="outer")
        inner = div.div(_class="inner")
        inner.span("deep")

    _, out = _render_pretty(build)
    assert out == (
        "<body>\n"
        '  <div class="outer">\n'
        '    <div class="inner">\n'
        "      <span>deep</span>\n"
        "    </div>\n"
        "  </div>\n"
        "</body>\n"
    )


def test_html_render_default_is_not_pretty():
    """pretty=False is the default; output stays linear."""
    _, out = _render(lambda root: root.body().h1("Hi"))
    assert "\n" not in out


def test_html_render_returns_string_when_target_is_none():
    _, out = _render(lambda root: root.div("a"))
    assert isinstance(out, str)


def test_html_render_target_writes_to_writable():
    class _Page(HtmlBuilderHandler):
        def main(self, root):
            root.div("a")

    page = _Page()
    page.create()
    buf = io.StringIO()
    page.set_render_target("html", buf, default=True)
    result = page.render()
    assert result is None
    assert buf.getvalue() == "<div>a</div>"


def test_html_render_target_invalid_object_raises_type_error():
    class _Page(HtmlBuilderHandler):
        def main(self, root):
            root.div("a")

    page = _Page()
    page.create()
    page.set_render_target("html", 42, default=True)  # neither writable nor callable
    with pytest.raises(TypeError):
        page.render()


# ----------------------------------------------------------------------
# Decision 8 (v0.4.0): renderer property.
# ----------------------------------------------------------------------


def test_handler_renderer_is_html_renderer_instance():
    from genro_builders.contrib.html.html_renderer import HtmlRenderer

    class _Page(HtmlBuilderHandler):
        def main(self, root):
            pass

    page = _Page()
    assert isinstance(page.renderer, HtmlRenderer)


def test_handler_renderer_is_cached():
    class _Page(HtmlBuilderHandler):
        def main(self, root):
            pass

    page = _Page()
    assert page.renderer is page.renderer


# ----------------------------------------------------------------------
# CSS kwarg feature on HtmlRenderer.
# ----------------------------------------------------------------------


def test_css_kwarg_root_emits_style():
    """A root-name kwarg (``color``) becomes a CSS property."""
    _, out = _render(lambda root: root.div("x", color="red"))
    assert out == '<div style="color: red">x</div>'


def test_css_kwarg_root_underscore_kebabifies():
    """``font_size`` matches root ``font`` → ``font-size``."""
    _, out = _render(lambda root: root.div("x", font_size="14px"))
    assert out == '<div style="font-size: 14px">x</div>'


def test_css_kwarg_subroot_padding_top():
    """``padding_top`` matches root ``padding`` → ``padding-top``."""
    _, out = _render(lambda root: root.div("x", padding_top="10px"))
    assert out == '<div style="padding-top: 10px">x</div>'


def test_css_kwarg_explicit_style_merged_kwargs_win():
    """``style="color: blue"`` + ``color="red"`` → ``color: red`` wins."""
    _, out = _render(lambda root: root.div("x", style="color: blue", color="red"))
    assert 'color: red' in out
    assert 'color: blue' not in out


def test_css_kwarg_style_escape_prefix():
    """``style_aspect_ratio="16 / 9"`` → ``style="aspect-ratio: 16 / 9"``."""
    _, out = _render(lambda root: root.div("x", style_aspect_ratio="16 / 9"))
    assert out == '<div style="aspect-ratio: 16 / 9">x</div>'


def test_css_kwarg_html_attr_still_html_attr():
    """``id="main"`` is a real HTML attribute, must NOT go into style."""
    _, out = _render(lambda root: root.div("x", id="main", color="red"))
    assert 'id="main"' in out
    assert 'style="color: red"' in out


def test_macro_rounded_top_level():
    """``rounded=10`` → all four corners radius."""
    _, out = _render(lambda root: root.div("x", rounded=10))
    assert "border-top-left-radius: 10px" in out
    assert "border-top-right-radius: 10px" in out
    assert "border-bottom-left-radius: 10px" in out
    assert "border-bottom-right-radius: 10px" in out


def test_macro_rounded_subkwargs_override():
    """``rounded_top=5`` sets only the two top corners."""
    _, out = _render(
        lambda root: root.div("x", rounded=10, rounded_top=5),
    )
    assert "border-top-left-radius: 5px" in out
    assert "border-top-right-radius: 5px" in out
    assert "border-bottom-left-radius: 10px" in out


def test_macro_transform_subkwargs_compose():
    """``transform_rotate=45, transform_scale=2`` composes both functions."""
    _, out = _render(
        lambda root: root.div("x", transform_rotate=45, transform_scale=2),
    )
    assert 'transform:' in out
    assert 'rotate(45deg)' in out
    assert 'scale(2)' in out


def test_macro_filter_subkwargs_compose():
    """``filter_blur=10, filter_contrast=80`` composes the chain."""
    _, out = _render(
        lambda root: root.div("x", filter_blur=10, filter_contrast=80),
    )
    assert "filter:" in out
    assert "blur(10px)" in out
    assert "contrast(80)" in out
