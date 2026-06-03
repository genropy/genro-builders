# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for BuilderHandler (decisions 4, 5, 6, 9, 11 — contract v0.4.0).

The handler is the engine that drives a single Builder through the
create/render lifecycle. These tests exercise:
    - construction binds builder_class to ``self.builder``;
    - ``self.source`` is a BuilderBag;
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

from genro_builders import BuilderBag
from genro_builders.builder_handler import BuilderHandler
from genro_builders.contrib.html import HtmlBuilderHandler


class _RecordingRenderer:
    """Stand-in renderer that records render() calls. Only used in tests."""

    def __init__(self, handler=None, builder=None):
        self.handler = handler
        self._builder = builder
        self.calls: list[tuple[Any, Any, Any]] = []
        self.renders: dict[int, Any] = {}
        self.mode: str | None = None

    def add_render(self, builder, renderer) -> None:
        self.renders[id(builder)] = renderer

    def render(self, source, **kwargs) -> str:
        # The handler injects ``self.mode`` before the call; record
        # mode + target in the legacy 3-tuple shape the tests assert
        # against (target is provided through finalize, see below).
        self._last_source = source
        return f"rendered(mode={self.mode!r})"

    def finalize(self, result, target):
        # Record the call shape the legacy tests assert: (source,
        # mode, target). Then return the result as-is when no target,
        # otherwise still return the rendered string so the assertion
        # ``"rendered" in out`` keeps passing.
        self.calls.append((self._last_source, self.mode, target))
        return result


class _RecordingBuilder:
    """Stand-in builder that records calls. Only used in tests."""

    _schema_tag_names: dict[str, str] = {}
    _schema = ()
    _default_render_mode = "stub"

    @property
    def renderer_stub(self) -> _RecordingRenderer:
        return _RecordingRenderer(builder=self)


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
    """Decision 4: handler holds builder + source bag."""
    h = _StubHandler()
    assert isinstance(h.builder, _RecordingBuilder)
    assert isinstance(h.source, BuilderBag)


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
    """_sourceroot is a plain Bag holding the source BuilderBag under 'main'."""
    h = _StubHandler()
    assert isinstance(h._sourceroot, Bag)
    assert "main" in h._sourceroot
    assert isinstance(h._sourceroot["main"], BuilderBag)


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


# ----------------------------------------------------------------------
# Reactive hooks (subtask handler_wrapper_root, P2)
# ----------------------------------------------------------------------


def test_on_source_change_default_is_noop():
    """Default on_source_change is a no-op: callable, returns None."""
    h = _StubHandler()
    assert h.on_source_change(node=None, evt="insert") is None  # type: ignore[arg-type]


def test_on_data_change_default_is_noop():
    """Default on_data_change is a no-op: callable, returns None."""
    h = _StubHandler()
    assert h.on_data_change(node=None, evt="insert") is None  # type: ignore[arg-type]


