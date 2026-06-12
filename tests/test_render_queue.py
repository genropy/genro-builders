# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Render queue: mount-name keys, source-relative paths.

The builder owns its mount name (passed at construction); the structural
source-wrapper segment (``SOURCE_ROOT``) is never an address. Source and
data events must therefore queue under the same key (the mount name) and
with the same path format (relative to ``builder.source``), whatever the
mount name is — historically everything was mounted as ``main`` and the
wrapper key happened to coincide.
"""
from __future__ import annotations

from genro_builders.builder import BuilderHandler
from genro_builders.contrib.html import HtmlBuilder


class _Page(HtmlBuilder):
    def main(self, root) -> None:
        body = root.body()
        body.data_setter("counter", 5)
        body.div("^counter", node_id="d1")


class _SharedReader(HtmlBuilder):
    def main(self, root) -> None:
        root.body().div("^_:index", node_id="shared")


def _reactive(*builders):
    handler = BuilderHandler(application=object())
    for builder in builders:
        builder.set_render_target(lambda text: None)   # discard output
    handler.add_builder(*builders)
    handler.activate()
    return handler


def test_data_event_queues_mount_name_and_source_relative_path():
    page = _Page(name="page")
    handler = _reactive(page)
    with handler.live():
        handler.data["page.counter"] = 99
        assert handler._nodes_to_render == {"page": [("upd", "body.div_0", None, None)]}


def test_source_event_queues_mount_name_and_source_relative_path():
    page = _Page(name="page")
    handler = _reactive(page)
    with handler.live():
        page.node_by_id("d1").set_attr(title="x")
        assert handler._nodes_to_render == {"page": [("upd", "body.div_0", None, None)]}


def test_live_flush_renders_a_non_main_mount(tmp_path):
    target = tmp_path / "out.html"
    page = _Page(name="page")
    handler = BuilderHandler(application=object())
    page.set_render_target(str(target))
    handler.add_builder(page)
    handler.activate()
    with handler.live():
        handler.data["page.counter"] = 99
        page.node_by_id("d1").set_attr(title="x")
    assert "99" in target.read_text(encoding="utf-8")


def test_shared_datum_queues_every_reader_under_its_own_mount_name():
    left = _SharedReader(name="left")
    right = _SharedReader(name="right")
    handler = _reactive(left, right)
    with handler.live():
        handler.data["_.index"] = 1
        assert handler._nodes_to_render == {
            "left": [("upd", "body.div_0", None, None)],
            "right": [("upd", "body.div_0", None, None)],
        }


def test_add_builder_rejects_duplicate_and_reserved_names():
    import pytest

    handler = BuilderHandler()
    handler.add_builder(_Page(name="page"))
    with pytest.raises(ValueError, match="already mounted"):
        handler.add_builder(_Page(name="page"))
    with pytest.raises(ValueError, match="shared data segment"):
        handler.add_builder(_Page(name="_"))


def test_name_defaults_to_dialect_typology():
    page = _Page()
    assert page.name == "html"


def test_autocreate_events_are_ignored():
    """One deep write = one logical mutation: the intermediate containers
    born on the way to the leaf (reason='autocreate') trigger neither
    compute nor render — the leaf event of the same write follows at
    once. With a reader on the container, one queue entry, not one per
    autocreated ancestor."""
    class Reader(HtmlBuilder):
        def main(self, root) -> None:
            root.body().div("^box", node_id="r")

    page = Reader(name="page")
    handler = _reactive(page)
    page.render()                       # register the ^box reader
    with handler.live():
        handler.data.set_item("page.box.a.b.leaf", 1)
        queued = [p for v in handler._nodes_to_render.values() for p in v]
        assert len(queued) == 1, queued
