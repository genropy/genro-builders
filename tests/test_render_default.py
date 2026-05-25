# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for ``BuilderHandler.render`` dispatch on a real dialect.

Verifies the framework-level rendering behavior using ``HtmlBuilder``:
default mode resolution, the always-available ``xml`` mode, pretty
output, unknown-mode rejection, and ``render_target`` handling.
"""
from __future__ import annotations

import io

import pytest

from genro_builders.contrib.html import HtmlBuilderHandler


class _Page(HtmlBuilderHandler):
    def main(self, root):
        root.div("hello", _class="greeting")


def test_render_returns_string_when_target_is_none():
    h = _Page()
    h.create()
    out = h.render()
    assert isinstance(out, str)
    assert "div" in out
    assert "hello" in out


def test_render_default_mode_matches_dialect():
    """``render()`` uses the dialect's ``_default_render_mode``."""
    h = _Page()
    h.create()
    assert h.render() == h.render(mode="html")


def test_render_xml_mode_matches_source_to_xml():
    """The ``xml`` mode is always available and equals ``source.to_xml()``."""
    h = _Page()
    h.create()
    assert h.render(mode="xml") == h.source.to_xml()


def test_render_xml_pretty_produces_multiline_output():
    """``pretty=True`` on xml mode produces a multi-line indented string."""
    h = _Page()
    h.create()
    pretty = h.render(mode="xml", pretty=True)
    linear = h.render(mode="xml")
    assert pretty != linear
    assert "\n" in pretty
    assert "\n" not in linear


def test_render_xml_doc_header_true_emits_xml_declaration():
    """``doc_header=True`` prepends the standard XML declaration."""
    h = _Page()
    h.create()
    text = h.render(mode="xml", doc_header=True)
    assert text.startswith("<?xml version='1.0' encoding='UTF-8'?>")


def test_render_xml_doc_header_custom_string_prepended_verbatim():
    """A custom ``doc_header`` string is prepended verbatim."""
    h = _Page()
    h.create()
    text = h.render(mode="xml", doc_header="<!DOCTYPE foo>")
    assert text.startswith("<!DOCTYPE foo>")


def test_render_unknown_mode_raises_value_error():
    h = _Page()
    h.create()
    with pytest.raises((ValueError, KeyError)):
        h.render(mode="xyz")


def test_render_target_writes_to_writable_object():
    """A render_target with a .write method receives the output."""
    h = _Page()
    h.create()
    buffer = io.StringIO()
    h.set_render_target("html", buffer, default=True)
    result = h.render()
    assert result is None
    assert "div" in buffer.getvalue()


def test_render_target_calls_callable_target():
    h = _Page()
    h.create()
    captured: list[str] = []
    h.set_render_target("html", captured.append, default=True)
    result = h.render()
    assert result is None
    assert len(captured) == 1
    assert "div" in captured[0]


def test_render_target_invalid_object_raises_type_error():
    h = _Page()
    h.create()
    h.set_render_target("html", object(), default=True)
    with pytest.raises(TypeError):
        h.render()


def test_render_target_writes_to_str_path(tmp_path):
    h = _Page()
    h.create()
    out = tmp_path / "page.html"
    h.set_render_target("html", str(out), default=True)
    result = h.render()
    assert result is None
    text = out.read_text(encoding="utf-8")
    assert "div" in text
    assert "hello" in text


def test_render_target_writes_to_pathlib_path(tmp_path):
    h = _Page()
    h.create()
    out = tmp_path / "page.html"
    h.set_render_target("html", out, default=True)
    result = h.render()
    assert result is None
    assert "div" in out.read_text(encoding="utf-8")


def test_render_target_path_creates_missing_parent_dirs(tmp_path):
    h = _Page()
    h.create()
    out = tmp_path / "deep" / "nested" / "page.html"
    assert not out.parent.exists()
    h.set_render_target("html", out, default=True)
    h.render()
    assert out.exists()
    assert "div" in out.read_text(encoding="utf-8")


def test_render_target_argument_overrides_registered(tmp_path):
    """target= passed to render() wins over set_render_target."""
    h = _Page()
    h.create()
    out_default = tmp_path / "default.html"
    out_override = tmp_path / "override.html"
    h.set_render_target("html", out_default, default=True)
    h.render(target=out_override)
    assert out_override.exists()
    assert not out_default.exists()


def test_render_target_false_forces_string(tmp_path):
    """target=False forces string return even if a target is registered."""
    h = _Page()
    h.create()
    out = tmp_path / "page.html"
    h.set_render_target("html", out, default=True)
    result = h.render(target=False)
    assert isinstance(result, str)
    assert "div" in result
    assert not out.exists()


def test_render_shortcut_render_html():
    """The auto-generated render_<mode> shortcut delegates to render()."""
    h = _Page()
    h.create()
    direct = h.render(mode="html")
    via_shortcut = h.render_html()
    assert direct == via_shortcut


def test_render_shortcut_unknown_mode_raises():
    """render_<mode> is generated only if the mode is registered."""
    h = _Page()
    h.create()
    with pytest.raises(AttributeError):
        h.render_xyz()
