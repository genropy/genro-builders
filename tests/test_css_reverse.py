# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for the CSS reverse: parser wrapper smoke + visitor + classmethods."""
from __future__ import annotations

import ast
import io
from pathlib import Path

import pytest

pytest.importorskip("tree_sitter_css")

from genro_builders.contrib.css import CssBuilder  # noqa: E402
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


def test_class_with_pseudo_plus_functional_falls_back_to_raw():
    """A plain pseudo (``:active``) attached to a class is normally
    folded into ``_class``, but as soon as a functional pseudo
    (``:not(...)``) joins the chain the whole selector must go to
    ``raw=`` — the strict ``_class`` regex on the renderer rejects
    parentheses, dots and commas inside the class string."""
    code = _reverse(".multibutton:active:not(.multibutton_selected) { color: red; }")
    assert "raw=" in code
    assert "_class=" not in code


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


def test_empty_source_emits_stylesheet_only_main():
    """Empty input still opens a stylesheet — the reverse always
    targets a whole CSS document, never a fragment."""
    code = _reverse("")
    assert "class ReversedCss(CssBuilderHandler):" in code
    assert "def main(self, root):" in code
    assert "sheet = root.stylesheet()" in code


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


# ---------------------------------------------------------------------------
# Phase 3: @media / @supports / CSS Nesting
# ---------------------------------------------------------------------------

def test_media_block_emits_rule_with_media_kwarg():
    css = "@media (max-width: 600px) { .a { width: 100%; } }"
    code = _reverse(css)
    assert "media='(max-width: 600px)'" in code
    assert "width='100%'" in code


def test_supports_block_emits_rule_with_supports_kwarg():
    css = "@supports (display: grid) { .a { display: grid; } }"
    code = _reverse(css)
    assert "supports='(display: grid)'" in code
    assert "display='grid'" in code


def test_supports_inside_media_combines_both_kwargs():
    css = (
        "@media (max-width: 600px) {"
        "  @supports (display: grid) {"
        "    .a { display: grid; }"
        "  }"
        "}"
    )
    code = _reverse(css)
    assert "media='(max-width: 600px)'" in code
    assert "supports='(display: grid)'" in code


def test_media_inside_supports_combines_both_kwargs():
    css = (
        "@supports (display: grid) {"
        "  @media (max-width: 600px) {"
        "    .a { display: grid; }"
        "  }"
        "}"
    )
    code = _reverse(css)
    assert "media='(max-width: 600px)'" in code
    assert "supports='(display: grid)'" in code


def test_css_nesting_produces_nested_selectors():
    css = ".card { padding: 8px; .title { font-size: 18px; } }"
    code = _reverse(css)
    # Outer selector and inner selector both present, both with own rule()
    assert code.count(".selector(") >= 2
    assert "_class='card'" in code
    assert "_class='title'" in code
    assert "padding='8px'" in code
    assert "font_size='18px'" in code


def test_nesting_with_ampersand_uses_raw():
    css = ".card { &:hover { color: red; } }"
    code = _reverse(css)
    assert "_class='card'" in code
    # &:hover not expressible structurally → raw
    assert "raw=" in code


def test_roundtrip_media_block():
    css = "@media (max-width: 600px) { .a { width: 100%; } }"
    out = _roundtrip(css)
    assert "@media (max-width: 600px)" in out
    assert "width: 100%" in out


def test_roundtrip_supports_block():
    css = "@supports (display: grid) { .a { display: grid; } }"
    out = _roundtrip(css)
    assert "@supports (display: grid)" in out
    assert "display: grid" in out


def test_roundtrip_css_nesting():
    css = ".card { padding: 8px; .title { font-size: 18px; } }"
    out = _roundtrip(css)
    assert ".card" in out
    assert ".title" in out
    assert "padding: 8px" in out
    assert "font-size: 18px" in out


# ---------------------------------------------------------------------------
# Phase 4: @import (import_statement) + stylesheet wrapping
# ---------------------------------------------------------------------------

def test_reverse_always_opens_stylesheet():
    """Even minimal CSS produces a stylesheet wrapper — the reverse
    targets whole documents, not fragments."""
    code = _reverse(".card { color: red; }")
    assert "sheet = root.stylesheet()" in code
    # selector calls go through sheet, not root
    assert "sheet.selector" in code
    assert "root.selector" not in code


def test_import_url_form():
    code = _reverse('@import url("reset.css");')
    assert "sheet.importcss(url='reset.css')" in code


def test_import_bare_string_form():
    code = _reverse('@import "foo.css";')
    assert "sheet.importcss(url='foo.css')" in code


def test_import_with_media_query():
    code = _reverse('@import url("phone.css") screen and (max-width: 600px);')
    assert "sheet.importcss(url='phone.css', media='screen and (max-width: 600px)')" in code


def test_import_with_layer_modifier_falls_back_to_comment():
    """tree-sitter-css 0.25 cannot parse layer(...); the reverse
    leaves a Python comment-string so the user knows to patch it."""
    code = _reverse('@import url("layered.css") layer(reset);')
    assert "importcss" not in code  # no half-true call emitted
    assert "layer/supports modifier not parsed" in code


def test_import_with_supports_modifier_falls_back_to_comment():
    code = _reverse('@import url("g.css") supports(display: grid);')
    assert "importcss" not in code
    assert "layer/supports modifier not parsed" in code


def test_roundtrip_simple_import():
    css = '@import url("reset.css");'
    out = _roundtrip(css)
    assert '@import url("reset.css")' in out


def test_roundtrip_import_with_media():
    css = '@import url("print.css") print;'
    out = _roundtrip(css)
    assert '@import url("print.css") print' in out


def test_imports_appear_before_selectors_in_round_trip():
    css = '@import url("reset.css"); .card { color: red; }'
    out = _roundtrip(css)
    import_pos = out.index('@import')
    card_pos = out.index('.card')
    assert import_pos < card_pos


# ---------------------------------------------------------------------------
# Phase 4: CssBuilder.from_css / from_css_file classmethods
# ---------------------------------------------------------------------------

CSS_FIXTURE = ".card { color: red; padding: 8px; }"


def test_from_css_returns_python_string_when_dest_none():
    out = CssBuilder.from_css(CSS_FIXTURE)
    assert isinstance(out, str)
    assert "class ReversedCss(CssBuilderHandler):" in out
    assert "sheet = root.stylesheet()" in out
    assert "_class='card'" in out


def test_from_css_writes_to_str_path(tmp_path):
    out = tmp_path / "generated.py"
    ret = CssBuilder.from_css(CSS_FIXTURE, str(out))
    assert ret is None
    text = out.read_text(encoding="utf-8")
    assert "class ReversedCss" in text


def test_from_css_writes_to_pathlib_path(tmp_path):
    out = tmp_path / "generated.py"
    ret = CssBuilder.from_css(CSS_FIXTURE, out)
    assert ret is None
    assert "class ReversedCss" in out.read_text(encoding="utf-8")


def test_from_css_creates_missing_parent_dirs(tmp_path):
    out = tmp_path / "deep" / "nested" / "g.py"
    assert not out.parent.exists()
    CssBuilder.from_css(CSS_FIXTURE, out)
    assert out.exists()


def test_from_css_writes_to_file_like_buffer():
    buf = io.StringIO()
    ret = CssBuilder.from_css(CSS_FIXTURE, buf)
    assert ret is None
    assert "class ReversedCss" in buf.getvalue()


def test_from_css_invokes_callable_target():
    captured: list[str] = []
    ret = CssBuilder.from_css(CSS_FIXTURE, captured.append)
    assert ret is None
    assert len(captured) == 1
    assert "class ReversedCss" in captured[0]


def test_from_css_rejects_unsupported_dest():
    with pytest.raises(TypeError):
        CssBuilder.from_css(CSS_FIXTURE, object())


def test_from_css_custom_class_name():
    out = CssBuilder.from_css(CSS_FIXTURE, class_name="MyTheme")
    assert out is not None
    assert "class MyTheme(CssBuilderHandler):" in out


def test_from_css_file_reads_from_path(tmp_path):
    src = tmp_path / "theme.css"
    src.write_text(CSS_FIXTURE, encoding="utf-8")
    out = CssBuilder.from_css_file(src)
    assert isinstance(out, str)
    assert "class ThemeStyle(CssBuilderHandler):" in out


def test_from_css_file_derives_class_name_from_stem(tmp_path):
    src = tmp_path / "dark_mode.css"
    src.write_text(CSS_FIXTURE, encoding="utf-8")
    out = CssBuilder.from_css_file(src)
    assert out is not None
    assert "class DarkModeStyle(CssBuilderHandler):" in out


def test_from_css_file_skips_leading_numeric_segment(tmp_path):
    """Filenames starting with a digit drop the first '_'-separated
    segment so the resulting class name is a valid Python identifier
    (e.g. ``00_gnr_resets.css`` -> ``class GnrResetsStyle``)."""
    src = tmp_path / "00_gnr_resets.css"
    src.write_text(CSS_FIXTURE, encoding="utf-8")
    out = CssBuilder.from_css_file(src)
    assert out is not None
    assert "class GnrResetsStyle(CssBuilderHandler):" in out
    # the generated code must be valid Python
    compile(out, "<test>", "exec")


def test_from_css_file_class_name_override(tmp_path):
    src = tmp_path / "theme.css"
    src.write_text(CSS_FIXTURE, encoding="utf-8")
    out = CssBuilder.from_css_file(src, class_name="Branded")
    assert out is not None
    assert "class Branded(CssBuilderHandler):" in out


def test_from_css_file_writes_dest(tmp_path):
    src = tmp_path / "theme.css"
    src.write_text(CSS_FIXTURE, encoding="utf-8")
    out = tmp_path / "theme.py"
    ret = CssBuilder.from_css_file(src, out)
    assert ret is None
    assert "class ThemeStyle" in out.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Phase 4: round-trip on a real-world CSS file (gnrbase_css)
# ---------------------------------------------------------------------------


_GNR_RESETS = Path(
    "/Users/gporcari/Sviluppo/Genropy/genropy/gnrjs/gnr_d11/css/"
    "gnrbase_css/00_gnr_resets.css",
)


@pytest.mark.skipif(
    not _GNR_RESETS.exists(),
    reason="local GenroPy CSS fixture not available",
)
def test_real_world_gnr_resets_roundtrip_executes_and_renders():
    """Smoke-level round-trip on a real GenroPy CSS file:
    reverse → exec → render produces a non-empty CSS that includes the
    expected @import directives and at least the .card-like selectors."""
    source = _GNR_RESETS.read_text(encoding="utf-8")
    code = CssBuilder.from_css(source)
    assert code is not None
    namespace: dict = {}
    exec(code, namespace)
    handler = namespace["ReversedCss"]()
    handler.create()
    out = handler.render()
    assert isinstance(out, str)
    assert "@import" in out
    assert "fonts.googleapis.com" in out
    # any of these touchstones from the original file should survive
    assert "outline: none" in out
    assert ":focus" in out
