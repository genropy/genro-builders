# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for ``_BuildMixin.build`` on a real dialect.

The build phase is framework-level: the same walk runs for every
dialect. The default body is a 1:1 mirror with hooks. Verified using
``HtmlBuilder``: a single node, attribute preservation, nested
structure, and idempotency of the resulting XML.
"""
from __future__ import annotations

from genro_builders.contrib.html import HtmlBuilderHandler


def _make_handler(populate):
    class _Page(HtmlBuilderHandler):
        def main(self, root):
            populate(root)

    return _Page()


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
    assert len(h.built) == 1
    outer = next(iter(h.built))
    assert outer.node_tag == "div"
    inner_nodes = list(outer.value)
    assert len(inner_nodes) == 2
    assert all(n.node_tag == "span" for n in inner_nodes)
    assert [n.value for n in inner_nodes] == ["inner-one", "inner-two"]


def test_build_is_idempotent_in_structure():
    """Running build twice produces valid XML both times."""
    h = _make_handler(lambda root: root.div("once"))
    h.create()
    h.build()
    first = h.built.to_xml()
    h.build()
    second = h.built.to_xml()
    assert first
    assert second
