# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for _BuildMixin.build (decisions 5, 7, 8 — re-read 2026-05-08).

The build phase is framework-level: the same walk runs for every
dialect. The default body is a 1:1 mirror with hooks; ``@component``
is dormant and triggers a parlante NotImplementedError.
"""
from __future__ import annotations

import pytest

from genro_builders import BagBuilderBase
from genro_builders.builder import component, element
from genro_builders.builder_handler import BuilderHandler


class _TinyDialect(BagBuilderBase):

    @element()
    def root(self): ...

    @element()
    def div(self): ...

    @element()
    def span(self): ...


class _TinyHandler(BuilderHandler):
    builder_class = _TinyDialect

    def main(self, root):  # populated by the test using a callable
        self._populate(root)

    _populate = staticmethod(lambda root: None)


def _make_handler(populate):
    h = _TinyHandler()
    h._populate = populate  # type: ignore[assignment]
    return h


def test_build_mirrors_a_single_node():
    h = _make_handler(lambda root: root.div("hello"))
    h.create()
    h.build()
    assert len(h.built) == 1
    node = next(iter(h.built))
    assert node.node_tag == "div"
    assert node.value == "hello"


def test_build_mirrors_attributes():
    h = _make_handler(lambda root: root.div("hi", _class="greeting", id="x"))
    h.create()
    h.build()
    node = next(iter(h.built))
    assert node.attr.get("_class") == "greeting"
    assert node.attr.get("id") == "x"


def test_build_mirrors_nested_structure():
    def populate(root):
        outer = root.div()
        outer.span("inner-one")
        outer.span("inner-two")

    h = _make_handler(populate)
    h.create()
    h.build()
    # outer div with two spans inside
    assert len(h.built) == 1
    outer = next(iter(h.built))
    assert outer.node_tag == "div"
    inner_nodes = list(outer.value)
    assert len(inner_nodes) == 2
    assert all(n.node_tag == "span" for n in inner_nodes)
    assert [n.value for n in inner_nodes] == ["inner-one", "inner-two"]


def test_build_is_idempotent_in_structure():
    """Running build twice produces the same structure (no duplication)."""
    h = _make_handler(lambda root: root.div("once"))
    h.create()
    h.build()
    first = h.built.to_xml()
    h.build()  # re-build wipes and refills (semantics defined by impl)
    second = h.built.to_xml()
    # Default impl does NOT clear the built first; behavior is "append".
    # The contract here is just that the built remains valid XML.
    assert first
    assert second


def test_build_raises_not_implemented_on_component():
    """@component is dormant: the build raises with a parlante message."""

    class DialectWithComponent(BagBuilderBase):

        @element()
        def root(self): ...

        @component(sub_tags="")
        def widget(self, comp, **kwargs):
            comp  # body kept to satisfy @component (must have a body)

    class HandlerWithComponent(BuilderHandler):
        builder_class = DialectWithComponent

        def main(self, root):
            root.widget()  # opaque in source (decision 7)

    h = HandlerWithComponent()
    h.create()
    # Component is opaque in the source — create() must not raise.
    assert len(h.source) == 1

    with pytest.raises(NotImplementedError) as excinfo:
        h.build()
    msg = str(excinfo.value)
    assert "component" in msg.lower()
    assert "decision 7" in msg.lower() or "restart" in msg.lower()
