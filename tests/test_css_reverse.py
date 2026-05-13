# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for the CSS reverse: parser wrapper smoke + visitor + classmethods."""
from __future__ import annotations

import ast

import pytest

pytest.importorskip("tree_sitter_css")

from genro_builders.contrib.css._reverse import CssReverser, _parse_css  # noqa: E402

# ---------------------------------------------------------------------------
# Parser smoke tests
# ---------------------------------------------------------------------------

def test_parse_css_returns_stylesheet_root():
    root = _parse_css(".foo { color: red; }")
    assert root.type == "stylesheet"


def test_parse_css_returns_empty_stylesheet_for_blank_source():
    root = _parse_css("")
    assert root.type == "stylesheet"
    assert root.named_child_count == 0


def test_parse_css_handles_at_rules():
    root = _parse_css("@media (max-width: 600px) { .a { width: 100%; } }")
    assert root.type == "stylesheet"
    kinds = [c.type for c in root.named_children]
    assert "media_statement" in kinds


# ---------------------------------------------------------------------------
# CssReverser unit tests (Phase 2: selectors, rules, vars)
# ---------------------------------------------------------------------------

def _reverse(css: str, class_name: str = "ReversedCss") -> str:
    """Helper: reverse ``css`` to Python source via CssReverser."""
    return ast.unparse(CssReverser(class_name=class_name).reverse(css))


def _roundtrip(css: str) -> str:
    """Helper: reverse ``css`` then exec the generated module and return the
    rendered CSS (pretty)."""
    code = _reverse(css)
    namespace: dict = {}
    exec(code, namespace)
    handler_cls = namespace["ReversedCss"]
    handler = handler_cls()
    handler.create()
    handler.build()
    return handler.render() or ""


def test_class_selector_simple():
    code = _reverse(".card { color: red; }")
    assert "_class='card'" in code
    assert "color='red'" in code


def test_id_selector():
    code = _reverse("#main { color: red; }")
    assert "id='main'" in code


def test_tag_selector():
    code = _reverse("button { color: red; }")
    assert "tag='button'" in code


def test_attribute_selector():
    code = _reverse('input[type="text"] { color: red; }')
    assert "attr=" in code
    assert "'type': 'text'" in code


def test_pseudo_class_attached_to_single_class():
    code = _reverse(".btn:hover { color: red; }")
    assert "_class='btn:hover'" in code


def test_pseudo_class_functional_falls_back_to_raw():
    code = _reverse(":not(.x) { color: red; }")
    assert "raw=" in code


def test_kebab_property_becomes_underscore_kwarg():
    code = _reverse(".a { background-color: red; font-size: 12px; }")
    assert "background_color='red'" in code
    assert "font_size='12px'" in code


def test_selector_list_emits_selector_list_then_selectors():
    code = _reverse(".a, .b, .c { color: red; }")
    assert "selector_list()" in code
    assert code.count(".selector(") >= 3
    assert "color='red'" in code


def test_custom_property_emits_cssvar():
    code = _reverse(":root { --brand: #3498db; }")
    assert "cssvar('brand', value='#3498db')" in code


def test_descendant_combinator_falls_back_to_raw():
    code = _reverse(".parent .child { color: red; }")
    assert "raw=" in code


def test_empty_source_emits_empty_main():
    code = _reverse("")
    assert "class ReversedCss(CssBuilderHandler):" in code
    assert "def main(self, root):" in code
    assert "pass" in code


def test_custom_class_name():
    code = _reverse(".a { color: red; }", class_name="Theme")
    assert "class Theme(CssBuilderHandler):" in code


def test_roundtrip_simple_rule():
    css = ".card { color: red; }"
    out = _roundtrip(css)
    assert ".card" in out
    assert "color: red" in out


def test_roundtrip_selector_list():
    css = ".a, .b { color: red; }"
    out = _roundtrip(css)
    assert ".a" in out
    assert ".b" in out
    assert "color: red" in out


def test_roundtrip_with_cssvar():
    css = ":root { --brand: #3498db; }"
    out = _roundtrip(css)
    assert "--brand: #3498db" in out
