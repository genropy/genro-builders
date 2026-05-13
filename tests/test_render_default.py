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
    h.build()
    out = h.render()
    assert isinstance(out, str)
    assert "div" in out
    assert "hello" in out


def test_render_default_mode_matches_dialect():
    """``render()`` uses ``_default_render_mode`` of the dialect."""
    h = _Page()
    h.create()
    h.build()
    assert h.render() == h.render("html")


def test_render_xml_mode_matches_built_to_xml():
    """The ``xml`` mode is always available and equals ``built.to_xml()``."""
    h = _Page()
    h.create()
    h.build()
    assert h.render("xml") == h.built.to_xml()


def test_render_xml_pretty_produces_multiline_output():
    """``pretty=True`` on xml mode produces a multi-line indented string."""
    h = _Page()
    h.create()
    h.build()
    pretty = h.render("xml", pretty=True)
    linear = h.render("xml")
    assert pretty != linear
    assert "\n" in pretty
    assert "\n" not in linear


def test_render_unknown_mode_raises_value_error():
    h = _Page()
    h.create()
    h.build()
    with pytest.raises(ValueError):
        h.render("xyz")


def test_render_target_writes_to_writable_object():
    """A render_target with a .write method receives the output."""
    h = _Page()
    h.create()
    h.build()
    buffer = io.StringIO()
    h.render_target = buffer
    result = h.render()
    assert result is None
    assert "div" in buffer.getvalue()


def test_render_target_calls_callable_target():
    h = _Page()
    h.create()
    h.build()
    captured: list[str] = []
    h.render_target = captured.append
    result = h.render()
    assert result is None
    assert len(captured) == 1
    assert "div" in captured[0]


def test_render_target_invalid_object_raises_type_error():
    h = _Page()
    h.create()
    h.build()
    h.render_target = object()  # not writable, not callable
    with pytest.raises(TypeError):
        h.render()


def test_render_target_writes_to_str_path(tmp_path):
    h = _Page()
    h.create()
    h.build()
    out = tmp_path / "page.html"
    h.render_target = str(out)
    result = h.render()
    assert result is None
    text = out.read_text(encoding="utf-8")
    assert "div" in text
    assert "hello" in text


def test_render_target_writes_to_pathlib_path(tmp_path):
    h = _Page()
    h.create()
    h.build()
    out = tmp_path / "page.html"
    h.render_target = out
    result = h.render()
    assert result is None
    assert "div" in out.read_text(encoding="utf-8")


def test_render_target_path_creates_missing_parent_dirs(tmp_path):
    h = _Page()
    h.create()
    h.build()
    out = tmp_path / "deep" / "nested" / "page.html"
    assert not out.parent.exists()
    h.render_target = out
    h.render()
    assert out.exists()
    assert "div" in out.read_text(encoding="utf-8")
