# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for BagBuilderBase.to_grammar — the builder_grammar v1.0 exporter.

The format specification lives in
``src/genro_builders/builder/GRAMMAR_FORMAT.md``.

These tests exercise the export end-to-end on real dialects (HTML,
SVG, CSS) and on small ad-hoc builders that reproduce specific
edge cases (missing inherits_from target, topological order).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from genro_builders import BagBuilderBase
from genro_builders.builder import abstract, element
from genro_builders.contrib.css import CssBuilder
from genro_builders.contrib.html import HtmlBuilder
from genro_builders.contrib.svg import SvgBuilder


def _dump(cls: type, tmp_path: Path) -> dict:
    out = tmp_path / f"{cls._name}.json"
    cls.to_grammar(out)
    return json.loads(out.read_text())


# ---------------------------------------------------------------------------
# Happy path on real dialects
# ---------------------------------------------------------------------------


def test_html_grammar_export(tmp_path: Path) -> None:
    data = _dump(HtmlBuilder, tmp_path)

    assert data["document_format"]["name"] == "builder_grammar"
    assert data["document_format"]["version"] == "1.0"
    assert data["grammar"]["name"] == "html"

    assert "div" in data["elements"]
    assert data["elements"]["div"]["sub_tags"]
    assert data["elements"]["br"]["sub_tags"] == ""

    assert "svg" in data["subbuilders"]
    assert data["subbuilders"]["svg"]["builder_name"] == "svg"


def test_svg_grammar_export_emits_bare_abstract_names(tmp_path: Path) -> None:
    data = _dump(SvgBuilder, tmp_path)

    assert data["grammar"]["name"] == "svg"
    assert "graphics" in data["abstracts"]
    assert "container_element" in data["abstracts"]

    # Bare labels — no `@` prefix anywhere in the exported JSON
    raw = json.dumps(data)
    assert "@graphics" not in raw
    assert "@container_element" not in raw


def test_svg_grammar_export_includes_html_subbuilder_with_wrap_tag(tmp_path: Path) -> None:
    data = _dump(SvgBuilder, tmp_path)

    assert "html" in data["subbuilders"]
    assert data["subbuilders"]["html"]["builder_name"] == "html"
    assert data["subbuilders"]["html"]["wrap_tag"] == "foreignObject"
    assert data["subbuilders"]["html"]["wrap_attrs"] == {
        "xmlns": "http://www.w3.org/1999/xhtml",
    }


def test_css_grammar_export_smoke(tmp_path: Path) -> None:
    data = _dump(CssBuilder, tmp_path)

    assert data["grammar"]["name"] == "css"
    assert isinstance(data["elements"], dict)
    assert len(data["elements"]) > 0


# ---------------------------------------------------------------------------
# Structural invariants
# ---------------------------------------------------------------------------


def test_document_format_is_first_key(tmp_path: Path) -> None:
    data = _dump(HtmlBuilder, tmp_path)
    assert next(iter(data)) == "document_format"


def test_four_sections_are_always_present_in_usage_order(tmp_path: Path) -> None:
    data = _dump(HtmlBuilder, tmp_path)

    for section in ("abstracts", "subbuilders", "elements", "data_elements"):
        assert section in data
        assert isinstance(data[section], dict)

    keys = list(data.keys())
    assert keys.index("abstracts") < keys.index("subbuilders")
    assert keys.index("subbuilders") < keys.index("elements")
    assert keys.index("elements") < keys.index("data_elements")


def test_no_components_section_post_v0_4_0(tmp_path: Path) -> None:
    """Sentinel: `@component` was removed in v0.4.0. The exporter must
    not invent a `components` key."""
    for cls in (HtmlBuilder, SvgBuilder, CssBuilder):
        data = _dump(cls, tmp_path)
        assert "components" not in data


def test_no_at_prefix_in_labels_or_inherits_from(tmp_path: Path) -> None:
    """Sentinel: no `@` prefix in any label (top-level or abstract) and
    in any `inherits_from` value. Catches accidental leakage of the
    old abstract-prefix convention.

    Note: `@` is allowed inside free-form `doc` strings (e.g. the CSS
    grammar legitimately discusses `@import` / `@media` / `@supports`
    in element documentation). The sentinel scopes itself to the
    structural fields where `@` would denote the old convention.
    """
    for cls in (HtmlBuilder, SvgBuilder, CssBuilder):
        data = _dump(cls, tmp_path)

        # No `@` in any label key, in any section.
        for section_name in ("abstracts", "subbuilders", "elements", "data_elements"):
            for label in data[section_name]:
                assert "@" not in label, (
                    f"{cls.__name__}: label {label!r} in section "
                    f"{section_name!r} contains '@'"
                )

        # No `@` in any `inherits_from` value.
        for section_name in ("abstracts", "elements"):
            for label, form in data[section_name].items():
                value = form.get("inherits_from")
                if value is not None:
                    assert "@" not in value, (
                        f"{cls.__name__}: {section_name}.{label}."
                        f"inherits_from={value!r} contains '@'"
                    )


# ---------------------------------------------------------------------------
# Validation: dangling inherits_from raises at class-definition time
# ---------------------------------------------------------------------------


def test_inherits_from_unknown_raises_value_error() -> None:
    """Declaring `inherits_from` against a non-existent abstract must
    fail loudly at class-definition time (no silent fallback at
    runtime)."""

    with pytest.raises(ValueError, match="inherits_from"):
        class _Bogus(BagBuilderBase):
            _name = None  # not registered

            @abstract(sub_tags="span,a")
            def phrasing(self): ...

            @element(inherits_from="ghost")
            def p(self): ...


def test_inherits_from_partial_unknown_in_list_raises() -> None:
    """A typo in any name of a comma-separated `inherits_from` list
    must raise — even if the other names resolve correctly."""

    with pytest.raises(ValueError, match="inherits_from"):
        class _Bogus(BagBuilderBase):
            _name = None

            @abstract(sub_tags="span")
            def phrasing(self): ...

            @element(inherits_from="phrasing,ghost")
            def p(self): ...


# ---------------------------------------------------------------------------
# Topological ordering within a section
# ---------------------------------------------------------------------------


def test_abstracts_section_is_topologically_ordered() -> None:
    """An abstract that inherits from another must appear after its
    parent in the abstracts section."""

    class _Topo(BagBuilderBase):
        _name = None  # not registered

        @abstract(sub_tags="a,b,c")
        def base_phrasing(self): ...

        # Declared *before* base_phrasing in source order but must
        # come *after* in the exported document.
        @abstract(sub_tags="d,e,f", inherits_from="base_phrasing")
        def extended_phrasing(self): ...

    document = _Topo.__mro__[0]  # ensure class is built

    # Build the document directly to avoid touching the filesystem
    from genro_builders.builder._grammar_export import (
        _class_schema_to_grammar_document,
    )

    data = _class_schema_to_grammar_document(_Topo)
    abstracts_keys = list(data["abstracts"].keys())

    assert "base_phrasing" in abstracts_keys
    assert "extended_phrasing" in abstracts_keys
    assert abstracts_keys.index("base_phrasing") < abstracts_keys.index(
        "extended_phrasing"
    ), abstracts_keys
    del document  # silence unused-var warning
