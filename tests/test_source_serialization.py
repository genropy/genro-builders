# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""The source bag must remain a Bag (decision 5 v0.4.0).

The source is the user's recipe (also serialized by render). Any
builder/handler machinery on top must not break standard genro-bag
serialization (``to_xml()`` and other serializers).
"""
from __future__ import annotations

from genro_builders import BuilderSource
from genro_builders.contrib.html import HtmlBuilderHandler


def test_empty_source_bag_serializes_to_xml():
    bag = BuilderSource()
    out = bag.to_xml()
    assert isinstance(out, str)


def test_plain_source_bag_to_xml_round_trip():
    bag = BuilderSource()
    bag.set_item("alfa", "hello")
    bag.set_item("beta", 42)
    out = bag.to_xml()
    assert "<alfa>hello</alfa>" in out
    assert "<beta>42</beta>" in out


def test_nested_source_bag_to_xml():
    bag = BuilderSource()
    bag.set_item("container", BuilderSource())
    bag.get_item("container").set_item("inner", "nested")
    out = bag.to_xml()
    assert "<container>" in out
    assert "<inner>nested</inner>" in out


def test_source_after_grammar_dispatch_serializes_to_xml():
    """The source produced by handler.create() must still serialize."""

    class _Page(HtmlBuilderHandler):
        def main(self, root):
            root.div("aaa", _class="greeting")

    h = _Page()
    h.create()
    out = h.source.to_xml()
    assert isinstance(out, str)
    assert "div" in out
    assert "aaa" in out
    assert "greeting" in out
