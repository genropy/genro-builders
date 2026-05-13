# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""End-to-end tests for CssBuilder + CssBuilderHandler (level 1)."""

from __future__ import annotations

import pytest

from genro_builders import BagBuilderBase
from genro_builders.contrib.css import CssBuilder, CssBuilderHandler


def _render(main_fn):
    """Build a handler with the given ``main`` and return its render output."""

    class _Page(CssBuilderHandler):
        def main(self, root):
            main_fn(root)

    page = _Page()
    page.create()
    page.build()
    return page.render()


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_css_builder_is_registered():
    assert BagBuilderBase.get_builder_class("css") is CssBuilder


def test_css_builder_has_canonical_name():
    assert CssBuilder._name == "css"


def test_css_render_default_mode_is_css():
    assert CssBuilder._default_render_mode == "css"


# ---------------------------------------------------------------------------
# Rule + selector + properties
# ---------------------------------------------------------------------------


def test_fragment_single_rule():
    def build(root):
        r = root.rule(color="red", font_size="14px")
        r.selector(_class="card")

    out = _render(build)
    assert out == ".card {\n  color: red;\n  font-size: 14px;\n}\n"


def test_stylesheet_with_multiple_rules():
    def build(root):
        sheet = root.stylesheet()
        r1 = sheet.rule(color="red")
        r1.selector(_class="a")
        r2 = sheet.rule(color="blue")
        r2.selector(_class="b")

    out = _render(build)
    assert out == ".a {\n  color: red;\n}\n.b {\n  color: blue;\n}\n"


def test_multi_selector_comma_separated():
    def build(root):
        r = root.rule(color="white")
        r.selector(_class="a")
        r.selector(_class="b")
        r.selector(_class="c")

    out = _render(build)
    assert out == ".a, .b, .c {\n  color: white;\n}\n"


def test_property_kebab_case_conversion():
    def build(root):
        r = root.rule(background_color="#fff", font_size="12px")
        r.selector(_class="x")

    out = _render(build)
    assert "background-color: #fff;" in out
    assert "font-size: 12px;" in out


# ---------------------------------------------------------------------------
# Selector kwargs
# ---------------------------------------------------------------------------


def test_selector_tag_id_class():
    def build(root):
        r = root.rule(color="red")
        r.selector(tag="div", id="main", _class="card")

    out = _render(build)
    assert "div#main.card" in out


def test_selector_multiple_classes_with_classes_kwarg():
    def build(root):
        r = root.rule(color="red")
        r.selector(classes=["card", "featured"])

    out = _render(build)
    assert ".card.featured" in out


def test_selector_class_with_pseudo_attached():
    def build(root):
        r = root.rule(color="red")
        r.selector(_class="foo:hover")

    out = _render(build)
    assert ".foo:hover" in out


def test_selector_attr_with_value():
    def build(root):
        r = root.rule(padding="8px")
        r.selector(tag="input", attr={"type": "text"})

    out = _render(build)
    assert 'input[type="text"]' in out


def test_selector_attr_without_value():
    def build(root):
        r = root.rule(padding="8px")
        r.selector(attr={"data-active": None})

    out = _render(build)
    assert "[data-active]" in out


def test_selector_raw_alone():
    def build(root):
        r = root.rule(opacity="0.5")
        r.selector(raw=".card:not(.disabled)")

    out = _render(build)
    assert ".card:not(.disabled)" in out


def test_selector_raw_appended_to_compound():
    def build(root):
        r = root.rule(color="green")
        r.selector(_class="card", raw="> .icon")

    out = _render(build)
    assert ".card > .icon" in out


# ---------------------------------------------------------------------------
# Validation errors
# ---------------------------------------------------------------------------


def test_selector_class_with_space_is_rejected():
    def build(root):
        r = root.rule(color="red")
        r.selector(_class="card featured")

    with pytest.raises(ValueError, match=r"selector class 'card featured'"):
        _render(build)


def test_selector_class_with_dot_is_rejected():
    def build(root):
        r = root.rule(color="red")
        r.selector(_class="card.featured")

    with pytest.raises(ValueError, match=r"selector class 'card.featured'"):
        _render(build)


def test_selector_class_and_classes_mutually_exclusive():
    def build(root):
        r = root.rule(color="red")
        r.selector(_class="a", classes=["b", "c"])

    with pytest.raises(ValueError, match=r"_class.*classes"):
        _render(build)


def test_selector_with_no_kwargs_is_rejected():
    def build(root):
        r = root.rule(color="red")
        r.selector()

    with pytest.raises(ValueError, match=r"tag/id/_class/classes/attr/raw"):
        _render(build)


def test_rule_without_selector_is_rejected():
    def build(root):
        root.rule(color="red")

    with pytest.raises(ValueError, match=r"no selector children"):
        _render(build)


def test_selector_tag_starting_with_digit_is_rejected():
    def build(root):
        r = root.rule(color="red")
        r.selector(tag="1div")

    with pytest.raises(ValueError, match=r"selector tag '1div'"):
        _render(build)


# ---------------------------------------------------------------------------
# CSS variables
# ---------------------------------------------------------------------------


def test_cssvar_basic():
    def build(root):
        r = root.rule()
        r.selector(raw=":root")
        r.cssvar("primary-color", value="#3498db")
        r.cssvar("spacing", value="8px")

    out = _render(build)
    assert out == (
        ":root {\n"
        "  --primary-color: #3498db;\n"
        "  --spacing: 8px;\n"
        "}\n"
    )


def test_cssvar_with_inline_comment():
    def build(root):
        r = root.rule()
        r.selector(raw=":root")
        r.cssvar("primary", value="#3498db", comment="brand color")

    out = _render(build)
    assert "--primary: #3498db; /* brand color */" in out


def test_cssvar_with_block_comment_when_long():
    long = "This is a longer explanation that exceeds the inline threshold for sure"
    assert len(long) > 60

    def build(root):
        r = root.rule()
        r.selector(raw=":root")
        r.cssvar("primary", value="#3498db", comment=long)

    out = _render(build)
    assert f"/* {long} */\n  --primary: #3498db;" in out


# ---------------------------------------------------------------------------
# Rule comments
# ---------------------------------------------------------------------------


def test_rule_inline_comment_after_last_property():
    def build(root):
        r = root.rule(color="red", comment="brand red")
        r.selector(_class="card")

    out = _render(build)
    assert "color: red; /* brand red */" in out


def test_rule_block_comment_when_long():
    long = "A long explanation describing exactly why this rule exists for the team"
    assert len(long) > 60

    def build(root):
        r = root.rule(color="red", comment=long)
        r.selector(_class="card")

    out = _render(build)
    assert f"/* {long} */\n.card" in out


# ---------------------------------------------------------------------------
# Pretty vs minified
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Rule nesting
# ---------------------------------------------------------------------------


def test_nested_rule_renders_inside_parent_block():
    def build(root):
        card = root.rule(padding="8px")
        card.selector(_class="card")
        title = card.rule(font_size="18px")
        title.selector(_class="title")

    out = _render(build)
    assert out == (
        ".card {\n"
        "  padding: 8px;\n"
        "  .title {\n"
        "    font-size: 18px;\n"
        "  }\n"
        "}\n"
    )


def test_nested_rule_with_ampersand_passes_through():
    def build(root):
        card = root.rule(padding="8px")
        card.selector(_class="card")
        hover = card.rule(background_color="#eef")
        hover.selector(raw="&:hover")

    out = _render(build)
    assert "&:hover {" in out
    assert "background-color: #eef" in out


def test_nested_rule_with_combinator_via_raw():
    def build(root):
        card = root.rule(padding="8px")
        card.selector(_class="card")
        icon = card.rule(width="16px")
        icon.selector(raw="& > .icon")

    out = _render(build)
    assert "& > .icon {" in out


def test_deeply_nested_rules():
    def build(root):
        a = root.rule(padding="8px")
        a.selector(_class="a")
        b = a.rule(font_size="14px")
        b.selector(_class="b")
        c = b.rule(color="red")
        c.selector(raw="&:hover")

    out = _render(build)
    assert out == (
        ".a {\n"
        "  padding: 8px;\n"
        "  .b {\n"
        "    font-size: 14px;\n"
        "    &:hover {\n"
        "      color: red;\n"
        "    }\n"
        "  }\n"
        "}\n"
    )


def test_nested_rule_after_cssvar_keeps_order():
    def build(root):
        rt = root.rule()
        rt.selector(raw=":root")
        rt.cssvar("brand", value="#3498db")
        inner = rt.rule(color="var(--brand)")
        inner.selector(_class="branded")

    out = _render(build)
    assert out == (
        ":root {\n"
        "  --brand: #3498db;\n"
        "  .branded {\n"
        "    color: var(--brand);\n"
        "  }\n"
        "}\n"
    )


def test_nested_rule_inside_stylesheet():
    def build(root):
        sheet = root.stylesheet()
        card = sheet.rule(padding="8px")
        card.selector(_class="card")
        title = card.rule(font_size="18px")
        title.selector(_class="title")

    out = _render(build)
    assert ".card {" in out
    assert "  .title {" in out
    assert "    font-size: 18px;" in out


def test_nested_rule_multi_selector_parent():
    def build(root):
        outer = root.rule(color="red")
        outer.selector(_class="a")
        outer.selector(_class="b")
        inner = outer.rule(font_size="14px")
        inner.selector(_class="x")

    out = _render(build)
    assert out.startswith(".a, .b {")
    assert "  .x {" in out


def test_nested_rule_indent_kwarg():
    def build(root):
        card = root.rule(padding="8px")
        card.selector(_class="card")
        title = card.rule(font_size="18px")
        title.selector(_class="title")

    class _Page(CssBuilderHandler):
        def main(self, root):
            build(root)

    page = _Page()
    page.create()
    page.build()
    out = page.render(indent="    ")
    assert "    padding: 8px;" in out
    assert "    .title {" in out
    assert "        font-size: 18px;" in out


# ---------------------------------------------------------------------------
# Pretty vs minified
# ---------------------------------------------------------------------------


def test_render_pretty_false_produces_single_line():
    def build(root):
        r = root.rule(color="red", font_size="14px")
        r.selector(_class="card")

    class _Page(CssBuilderHandler):
        def main(self, root):
            build(root)

    page = _Page()
    page.create()
    page.build()
    out = page.render(pretty=False)
    assert out == ".card { color: red; font-size: 14px; }"
