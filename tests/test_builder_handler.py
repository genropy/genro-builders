# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for BuilderHandler (decisions 4, 5, 6, 9, 11 — contract v0.4.0).

The handler is the engine that drives a single Builder through the
create/render lifecycle. These tests exercise:
    - construction binds builder_class to ``self.builder``;
    - ``self.source`` is a level-2 BuilderSource;
    - ``create()`` calls user-defined ``main(source)``;
    - ``render()`` delegates to the builder renderer with source,
      mode and render_target;
    - ``render_target`` is a settable property;
    - ``register_node_id`` / ``node_by_id`` honor the ``node_id -> path`` map.
"""
from __future__ import annotations

from typing import Any

import pytest

from genro_builders import BuilderSource
from genro_builders.builder_handler import BuilderHandler


class _RecordingRenderer:
    """Stand-in renderer that records render() calls. Only used in tests."""

    def __init__(self, handler):
        self.handler = handler
        self.calls: list[tuple[Any, Any, Any]] = []

    def render(self, source, mode=None, render_target=None, **kwargs) -> str:
        self.calls.append((source, mode, render_target))
        return f"rendered(mode={mode!r}, target={render_target!r})"


class _RecordingBuilder:
    """Stand-in builder that records calls. Only used in tests."""

    _schema_tag_names = frozenset()
    _schema = ()
    _default_render_mode = "stub"
    _renderers = {"stub": _RecordingRenderer}


class _StubHandler(BuilderHandler):
    builder_class = _RecordingBuilder

    def main(self, root) -> None:
        # set a marker we can assert against
        root.set_item("marker", "from-main")


def test_handler_requires_builder_class():
    """Decision 9: a handler subclass must declare a builder_class."""

    class NoBuilder(BuilderHandler):
        pass

    with pytest.raises(TypeError):
        NoBuilder()


def test_handler_instantiates_builder_and_source():
    """Decisions 4 and 12: handler holds builder + level-2 source."""
    h = _StubHandler()
    assert isinstance(h.builder, _RecordingBuilder)
    assert isinstance(h.source, BuilderSource)


def test_handler_attaches_itself_to_source():
    """Source knows its handler from birth (decision 4)."""
    h = _StubHandler()
    assert h.source._handler is h
    assert h.source._builder is h.builder


def test_create_invokes_main_with_source():
    """Decision 5: create() calls main(self.source)."""
    h = _StubHandler()
    h.create()
    assert h.source.get_item("marker") == "from-main"


def test_main_default_raises_not_implemented_error():
    """Subclasses must implement main()."""

    class HandlerWithoutMain(BuilderHandler):
        builder_class = _RecordingBuilder

    h = HandlerWithoutMain()
    with pytest.raises(NotImplementedError):
        h.create()


def test_render_delegates_to_renderer_with_source_mode_and_target():
    """Decision 6: handler.render() forwards source, mode and
    render_target to the dialect renderer."""
    h = _StubHandler()
    h.render_target = "<file-stub>"
    out = h.render("html")
    assert len(h.renderer.calls) == 1
    source_arg, mode_arg, target_arg = h.renderer.calls[0]
    assert source_arg is h.source
    assert mode_arg == "html"
    assert target_arg == "<file-stub>"
    assert "rendered" in out


def test_render_target_property_round_trip():
    """Decision 6: render_target is settable and readable."""
    h = _StubHandler()
    assert h.render_target is None
    h.render_target = "x"
    assert h.render_target == "x"


def test_register_node_id_and_node_by_id_round_trip():
    """Decision 11: register a node_id and look it up."""
    h = _StubHandler()
    h.source.set_item("alfa", None)
    h.register_node_id("anchor-1", "alfa")
    node = h.node_by_id("anchor-1")
    assert node is h.source.get_node("alfa")


def test_register_node_id_collision_raises():
    """Decision 11: explicit error on collision."""
    h = _StubHandler()
    h.register_node_id("anchor-1", "alfa")
    with pytest.raises(ValueError):
        h.register_node_id("anchor-1", "beta")


def test_register_node_id_idempotent_for_same_path():
    """Re-registering the same id with the same path is a no-op."""
    h = _StubHandler()
    h.register_node_id("anchor", "alfa")
    h.register_node_id("anchor", "alfa")  # must not raise
    assert h._node_index["anchor"] == "alfa"
