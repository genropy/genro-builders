# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""The source bag must remain a Bag (decision 7).

The source preserves the user's recipe and must be serializable
without semantic loss. ``to_xml()`` (and any other genro-bag
serializer) is therefore a contract on the source: any builder/handler
machinery added on top must not break it.
"""
from __future__ import annotations

from genro_builders import BuilderSourceBag
from genro_builders.contrib.html import HtmlBuilderHandler


def test_empty_source_bag_serializes_to_xml():
    bag = BuilderSourceBag()
    out = bag.to_xml()
    assert isinstance(out, str)


def test_plain_source_bag_to_xml_round_trip():
    bag = BuilderSourceBag()
    bag.set_item("alfa", "hello")
    bag.set_item("beta", 42)
    out = bag.to_xml()
    assert "<alfa>hello</alfa>" in out
    assert "<beta>42</beta>" in out


def test_nested_source_bag_to_xml():
    bag = BuilderSourceBag()
    bag.set_item("container", BuilderSourceBag())
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
