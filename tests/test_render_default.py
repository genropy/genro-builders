# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for the default render on BagBuilderBase (decision 6).

The base provides ``render_xml`` and instructs ``render(mode=None)``
to dispatch to the dialect's default mode (``xml`` on the base).
Concrete dialects can override either the default mode or the
``render_xml`` body; this module checks the base behavior only.
"""
from __future__ import annotations

import io

import pytest

from genro_builders import BagBuilderBase
from genro_builders.builder import element
from genro_builders.builder_handler import BuilderHandler


class _TinyDialect(BagBuilderBase):

    @element()
    def root(self): ...

    @element()
    def div(self): ...


class _TinyHandler(BuilderHandler):
    builder_class = _TinyDialect

    def main(self, root):
        root.div("hello", _class="greeting")


def test_render_returns_string_when_target_is_none():
    h = _TinyHandler()
    h.create()
    h.build()
    out = h.render()
    assert isinstance(out, str)
    assert "div" in out
    assert "hello" in out


def test_render_default_mode_is_xml():
    """Base default is ``xml``; output matches built.to_xml()."""
    h = _TinyHandler()
    h.create()
    h.build()
    assert h.render() == h.built.to_xml()


def test_render_explicit_xml_mode_matches_default():
    h = _TinyHandler()
    h.create()
    h.build()
    assert h.render("xml") == h.render()


def test_render_unknown_mode_raises_value_error():
    h = _TinyHandler()
    h.create()
    h.build()
    with pytest.raises(ValueError):
        h.render("html")  # base does not implement html


def test_render_target_writes_to_writable_object():
    """A render_target with a .write method receives the output."""
    h = _TinyHandler()
    h.create()
    h.build()
    buffer = io.StringIO()
    h.render_target = buffer
    result = h.render()
    assert result is None
    assert "div" in buffer.getvalue()


def test_render_target_calls_callable_target():
    h = _TinyHandler()
    h.create()
    h.build()
    captured: list[str] = []
    h.render_target = captured.append
    result = h.render()
    assert result is None
    assert len(captured) == 1
    assert "div" in captured[0]


def test_render_target_invalid_object_raises_type_error():
    h = _TinyHandler()
    h.create()
    h.build()
    h.render_target = object()  # not writable, not callable
    with pytest.raises(TypeError):
        h.render()


class _DialectWithCustomDefault(BagBuilderBase):

    _default_render_mode = "custom"

    @element()
    def root(self): ...

    def render_custom(self, built, render_target=None):
        text = "[custom render]"
        if render_target is None:
            return text
        render_target.write(text)
        return None


class _CustomHandler(BuilderHandler):
    builder_class = _DialectWithCustomDefault

    def main(self, root):
        pass


def test_dialect_can_override_default_render_mode():
    h = _CustomHandler()
    h.create()
    h.build()
    assert h.render() == "[custom render]"
