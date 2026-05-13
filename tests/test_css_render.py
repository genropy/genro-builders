# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""End-to-end tests for CssBuilder + CssBuilderHandler (level 1)."""

from __future__ import annotations

import pytest

from genro_builders import BagBuilderBase
from genro_builders.contrib.css import CssBuilder, CssBuilderHandler


def _render(main_fn, **render_kwargs):
    """Build a handler with the given ``main`` and return its render output."""

    class _Page(CssBuilderHandler):
        def main(self, root):
            main_fn(root)

    page = _Page()
    page.create()
    page.build()
    return page.render(**render_kwargs)


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
# Single selector + rule
# ---------------------------------------------------------------------------


def test_single_selector_with_rule():
    def build(root):
        s = root.selector(_class="card")
        s.rule(color="red", font_size="14px")

    out = _render(build)
    assert out == ".card {\n  color: red;\n  font-size: 14px;\n}\n"


def test_fragment_at_root_no_stylesheet():
    def build(root):
        s = root.selector(_class="card")
        s.rule(color="red")

    out = _render(build)
    assert out == ".card {\n  color: red;\n}\n"


def test_property_kebab_case_conversion():
    def build(root):
        s = root.selector(_class="x")
        s.rule(background_color="#fff", font_size="12px")

    out = _render(build)
    assert "background-color: #fff;" in out
    assert "font-size: 12px;" in out


# ---------------------------------------------------------------------------
# Selector kwargs
# ---------------------------------------------------------------------------


def test_selector_tag_id_class():
    def build(root):
        s = root.selector(tag="div", id="main", _class="card")
        s.rule(color="red")

    out = _render(build)
    assert "div#main.card" in out


def test_selector_classes_list():
    def build(root):
        s = root.selector(classes=["card", "featured"])
        s.rule(color="red")

    out = _render(build)
    assert ".card.featured" in out


def test_selector_class_with_pseudo():
    def build(root):
        s = root.selector(_class="foo:hover")
        s.rule(color="red")

    out = _render(build)
    assert ".foo:hover" in out


def test_selector_attr_with_value():
    def build(root):
        s = root.selector(tag="input", attr={"type": "text"})
        s.rule(padding="8px")

    out = _render(build)
    assert 'input[type="text"]' in out


def test_selector_attr_without_value():
    def build(root):
        s = root.selector(attr={"data-active": None})
        s.rule(padding="8px")

    out = _render(build)
    assert "[data-active]" in out


def test_selector_raw_alone():
    def build(root):
        s = root.selector(raw=".card:not(.disabled)")
        s.rule(opacity="0.5")

    out = _render(build)
    assert ".card:not(.disabled)" in out


def test_selector_raw_appended_to_compound():
    def build(root):
        s = root.selector(_class="card", raw="> .icon")
        s.rule(color="green")

    out = _render(build)
    assert ".card > .icon" in out


# ---------------------------------------------------------------------------
# selector_list
# ---------------------------------------------------------------------------


def test_selector_list_multiple_selectors():
    def build(root):
        sl = root.selector_list()
        sl.selector(_class="card")
        sl.selector(_class="panel")
        sl.selector(_class="dialog")
        sl.rule(color="white")

    out = _render(build)
    assert out == ".card, .panel, .dialog {\n  color: white;\n}\n"


def test_selector_list_in_stylesheet():
    def build(root):
        sheet = root.stylesheet()
        sl = sheet.selector_list()
        sl.selector(_class="a")
        sl.selector(_class="b")
        sl.rule(color="red")

    out = _render(build)
    assert ".a, .b {" in out
    assert "  color: red;" in out


def test_selector_list_with_cssvar():
    def build(root):
        sl = root.selector_list()
        sl.selector(raw=":root")
        sl.selector(raw=":host")
        sl.cssvar("brand", value="#3498db")

    out = _render(build)
    assert ":root, :host {" in out
    assert "  --brand: #3498db;" in out


def test_selector_list_with_no_selectors_raises():
    def build(root):
        sl = root.selector_list()
        sl.rule(color="red")

    with pytest.raises(ValueError, match=r"selector_list has no selector"):
        _render(build)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_selector_class_with_space_is_rejected():
    def build(root):
        s = root.selector(_class="card featured")
        s.rule(color="red")

    with pytest.raises(ValueError, match=r"selector class 'card featured'"):
        _render(build)


def test_selector_class_with_dot_is_rejected():
    def build(root):
        s = root.selector(_class="card.featured")
        s.rule(color="red")

    with pytest.raises(ValueError, match=r"selector class 'card.featured'"):
        _render(build)


def test_selector_class_and_classes_mutually_exclusive():
    def build(root):
        s = root.selector(_class="a", classes=["b", "c"])
        s.rule(color="red")

    with pytest.raises(ValueError, match=r"_class.*classes"):
        _render(build)


def test_selector_with_no_kwargs_is_rejected():
    def build(root):
        s = root.selector()
        s.rule(color="red")

    with pytest.raises(ValueError, match=r"tag/id/_class/classes/attr/raw"):
        _render(build)


def test_selector_tag_starting_with_digit_is_rejected():
    def build(root):
        s = root.selector(tag="1div")
        s.rule(color="red")

    with pytest.raises(ValueError, match=r"selector tag '1div'"):
        _render(build)


# ---------------------------------------------------------------------------
# CSS variables
# ---------------------------------------------------------------------------


def test_cssvar_basic():
    def build(root):
        s = root.selector(raw=":root")
        s.cssvar("primary-color", value="#3498db")
        s.cssvar("spacing", value="8px")

    out = _render(build)
    assert out == (
        ":root {\n"
        "  --primary-color: #3498db;\n"
        "  --spacing: 8px;\n"
        "}\n"
    )


def test_cssvar_with_inline_comment():
    def build(root):
        s = root.selector(raw=":root")
        s.cssvar("primary", value="#3498db", comment="brand color")

    out = _render(build)
    assert "--primary: #3498db; /* brand color */" in out


def test_cssvar_with_block_comment_when_long():
    long = "This is a longer explanation that exceeds the inline threshold for sure"
    assert len(long) > 60

    def build(root):
        s = root.selector(raw=":root")
        s.cssvar("primary", value="#3498db", comment=long)

    out = _render(build)
    assert f"/* {long} */" in out
    assert "  --primary: #3498db;" in out


# ---------------------------------------------------------------------------
# Comments on rule
# ---------------------------------------------------------------------------


def test_selector_inline_comment():
    def build(root):
        s = root.selector(_class="alert", comment="warning state")
        s.rule(color="red")

    out = _render(build)
    assert "color: red; /* warning state */" in out


def test_selector_block_comment():
    long = "A long explanation describing exactly why this rule exists for the team"
    assert len(long) > 60

    def build(root):
        s = root.selector(_class="card", comment=long)
        s.rule(color="red")

    out = _render(build)
    assert f"/* {long} */\n.card" in out


# ---------------------------------------------------------------------------
# Media variants
# ---------------------------------------------------------------------------


def test_rule_with_media_kwarg():
    def build(root):
        s = root.selector(_class="card")
        s.rule(width="300px")
        s.rule(media="(max-width: 600px)", width="100%")

    out = _render(build)
    assert out == (
        ".card {\n"
        "  width: 300px;\n"
        "  @media (max-width: 600px) {\n"
        "    .card {\n"
        "      width: 100%;\n"
        "    }\n"
        "  }\n"
        "}\n"
    )


def test_rule_media_with_type_in_string():
    def build(root):
        s = root.selector(_class="card")
        s.rule(color="white")
        s.rule(media="print", color="black")

    out = _render(build)
    assert "@media print {" in out
    assert "color: black;" in out


def test_rule_media_type_and_feature_combined():
    def build(root):
        s = root.selector(_class="card")
        s.rule(media="screen and (max-width: 600px)", padding="8px")

    out = _render(build)
    assert "@media screen and (max-width: 600px) {" in out


def test_rules_with_same_media_are_grouped():
    def build(root):
        s = root.selector(_class="card")
        s.rule(media="(max-width: 600px)", width="100%")
        s.rule(media="(max-width: 600px)", padding="8px")

    out = _render(build)
    # only one @media block, with both properties merged
    assert out.count("@media (max-width: 600px)") == 1
    assert "width: 100%;" in out
    assert "padding: 8px;" in out


def test_rules_with_different_media_are_separate_blocks():
    def build(root):
        s = root.selector(_class="card")
        s.rule(media="(max-width: 600px)", padding="8px")
        s.rule(media="(max-width: 400px)", padding="4px")

    out = _render(build)
    assert "@media (max-width: 600px) {" in out
    assert "@media (max-width: 400px) {" in out


def test_rule_media_inside_selector_list():
    def build(root):
        sl = root.selector_list()
        sl.selector(_class="a")
        sl.selector(_class="b")
        sl.rule(padding="16px")
        sl.rule(media="(max-width: 600px)", padding="8px")

    out = _render(build)
    assert ".a, .b {" in out
    assert "  @media (max-width: 600px) {" in out
    assert "    .a, .b {" in out


# ---------------------------------------------------------------------------
# Supports variants (kwarg on rule)
# ---------------------------------------------------------------------------


def test_rule_with_supports_kwarg():
    def build(root):
        s = root.selector(_class="grid")
        s.rule(display="flex")
        s.rule(supports="(display: grid)", display="grid")

    out = _render(build)
    assert "@supports (display: grid) {" in out
    assert "      display: grid;" in out


def test_rule_with_media_and_supports():
    def build(root):
        s = root.selector(_class="grid")
        s.rule(
            media="(max-width: 600px)",
            supports="(display: grid)",
            grid_template_columns="1fr",
        )

    out = _render(build)
    # supports wraps media
    assert "@supports (display: grid) {" in out
    assert "  @media (max-width: 600px) {" in out


# ---------------------------------------------------------------------------
# Nesting (CSS Nesting)
# ---------------------------------------------------------------------------


def test_nested_selector_inside_selector():
    def build(root):
        card = root.selector(_class="card")
        card.rule(padding="8px")
        title = card.selector(_class="title")
        title.rule(font_size="18px")

    out = _render(build)
    assert out == (
        ".card {\n"
        "  padding: 8px;\n"
        "  .title {\n"
        "    font-size: 18px;\n"
        "  }\n"
        "}\n"
    )


def test_nested_selector_with_ampersand():
    def build(root):
        card = root.selector(_class="card")
        card.rule(padding="8px")
        hover = card.selector(raw="&:hover")
        hover.rule(background_color="#eef")

    out = _render(build)
    assert "&:hover {" in out
    assert "background-color: #eef" in out


def test_deeply_nested_selectors():
    def build(root):
        a = root.selector(_class="a")
        a.rule(padding="8px")
        b = a.selector(_class="b")
        b.rule(font_size="14px")
        c = b.selector(raw="&:hover")
        c.rule(color="red")

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


# ---------------------------------------------------------------------------
# Pretty vs minified
# ---------------------------------------------------------------------------


def test_render_pretty_false_produces_single_line():
    def build(root):
        s = root.selector(_class="card")
        s.rule(color="red", font_size="14px")

    out = _render(build, pretty=False)
    assert out == ".card { color: red; font-size: 14px; }"


def test_render_custom_indent():
    def build(root):
        card = root.selector(_class="card")
        card.rule(padding="8px")
        title = card.selector(_class="title")
        title.rule(font_size="18px")

    out = _render(build, indent="    ")
    assert "    padding: 8px;" in out
    assert "    .title {" in out
    assert "        font-size: 18px;" in out
