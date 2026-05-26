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
from genro_bag import Bag

from genro_builders import BuilderSource
from genro_builders.builder_handler import BuilderHandler
from genro_builders.contrib.html import HtmlBuilderHandler


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

    _schema_tag_names: dict[str, str] = {}
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
    h.set_render_target("stub", "<file-stub>", default=True)
    out = h.render(mode="stub")
    assert len(h.renderer.calls) == 1
    source_arg, mode_arg, target_arg = h.renderer.calls[0]
    assert source_arg is h.source
    assert mode_arg == "stub"
    assert target_arg == "<file-stub>"
    assert "rendered" in out


def test_set_render_target_round_trip():
    """Decision 6: set_render_target stores target in the per-mode dict."""
    h = _StubHandler()
    assert h._render_targets == {}
    h.set_render_target("stub", "x")
    assert h._render_targets == {"stub": "x"}
    assert h._default_render_mode is None
    h.set_render_target("stub", "y", default=True)
    assert h._render_targets == {"stub": "y"}
    assert h._default_render_mode == "stub"


def test_node_id_kwarg_round_trip():
    """Decision 11: node_id passed as kwarg is recoverable via node_by_id."""

    class P(HtmlBuilderHandler):
        def main(self, root):
            root.body(node_id="anchor-1")

    page = P()
    page.create()
    node = page.node_by_id("anchor-1")
    assert node is page.source.get_node("body_0")


def test_node_id_kwarg_collision_raises():
    """Decision 11: two nodes with the same node_id raise ValueError."""

    class P(HtmlBuilderHandler):
        def main(self, root):
            body = root.body()
            body.div(node_id="dup")
            body.span(node_id="dup")

    with pytest.raises(ValueError, match="Duplicate node_id"):
        P().create()


def test_node_without_node_id_is_no_op():
    """Nodes without node_id don't pollute the index."""

    class P(HtmlBuilderHandler):
        def main(self, root):
            body = root.body()
            body.div()
            body.span(node_id="tagged")

    page = P()
    page.create()
    assert list(page._node_index.keys()) == ["tagged"]


def test_node_id_cleaned_on_delete():
    """Decision 11: removing a node de-registers its node_id."""

    class P(HtmlBuilderHandler):
        def main(self, root):
            body = root.body()
            body.div(node_id="tagged")

    page = P()
    page.create()
    assert page.node_by_id("tagged") is not None
    body = page.source.get_node("body_0").value
    del body["div_0"]
    with pytest.raises(KeyError):
        page.node_by_id("tagged")


# ----------------------------------------------------------------------
# Wrapper-root structure (subtask handler_wrapper_root, P1)
# ----------------------------------------------------------------------


def test_handler_has_sourceroot_wrapper():
    """_sourceroot is a plain Bag holding the BuilderSource under 'main'."""
    h = _StubHandler()
    assert isinstance(h._sourceroot, Bag)
    assert "main" in h._sourceroot
    assert isinstance(h._sourceroot["main"], BuilderSource)


def test_handler_has_dataroot_wrapper():
    """_dataroot is a plain Bag holding a plain Bag under 'main'."""
    h = _StubHandler()
    assert isinstance(h._dataroot, Bag)
    assert "main" in h._dataroot
    assert isinstance(h._dataroot["main"], Bag)


def test_handler_source_aliases_sourceroot_main():
    """self.source is the same object as _sourceroot['main']."""
    h = _StubHandler()
    assert h.source is h._sourceroot["main"]


def test_handler_data_aliases_dataroot_main():
    """self.data is the same object as _dataroot['main'] and is mutable."""
    h = _StubHandler()
    assert h.data is h._dataroot["main"]
    h.data["foo"] = 1
    assert h.data["foo"] == 1
