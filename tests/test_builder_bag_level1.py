# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for level 1 of the bag/node layering (decisions 3, 10, 12).

Level 1 = ``BuilderBag`` and ``BuilderBagNode`` obtained by combining
the genro-bag base classes with the builder-aware mixins. These tests
exercise only the surface implemented in fase 2.2.
"""
from __future__ import annotations

from genro_bag import Bag, BagNode

from genro_builders import BuilderBag, BuilderBagNode


def test_builder_bag_inherits_from_bag():
    """Decision 3: BuilderBag is Bag + mixin."""
    assert issubclass(BuilderBag, Bag)


def test_builder_bag_node_inherits_from_bag_node():
    """Decision 3: BuilderBagNode is BagNode + mixin."""
    assert issubclass(BuilderBagNode, BagNode)


def test_builder_bag_uses_builder_bag_node_as_node_class():
    """Nodes attached to a BuilderBag must be BuilderBagNode instances."""
    bag = BuilderBag()
    bag.set_item("hello", "world")
    node = bag.get_node("hello")
    assert isinstance(node, BuilderBagNode)


def test_builder_bag_carries_builder_and_handler_slots():
    """Decision 10: bag exposes _builder and _handler attributes."""
    bag = BuilderBag()
    assert bag._builder is None
    assert bag._handler is None


def test_builder_bag_node_has_builder_and_handler_slots():
    """Decision 10: node has _builder and _handler slots.

    Slots default to AttributeError when unset; this test sets them
    explicitly to confirm both slots accept values.
    """
    bag = BuilderBag()
    bag.set_item("alfa", None)
    node = bag.get_node("alfa")
    node._builder = "fake-builder"
    node._handler = "fake-handler"
    assert node._builder == "fake-builder"
    assert node._handler == "fake-handler"


def test_builder_bag_accepts_builder_and_handler_in_init():
    """Decision 4: bags receive their handler at construction."""
    sentinel_builder = object()
    sentinel_handler = object()
    bag = BuilderBag(builder=sentinel_builder, handler=sentinel_handler)
    assert bag._builder is sentinel_builder
    assert bag._handler is sentinel_handler


def test_builder_bag_without_builder_falls_back_to_normal_attribute_lookup():
    """A bag without a builder behaves like a plain Bag for attribute access."""
    bag = BuilderBag()
    bag.set_item("greeting", "hello")
    # No builder attached: 'greeting' resolves through the regular
    # ``__getattribute__`` path and would not exist as an attribute,
    # while ``get_item`` keeps working.
    assert bag.get_item("greeting") == "hello"


def test_builder_bag_dispatches_to_schema_when_builder_attached():
    """Decision 10: bag.<tag>(...) routes to builder._bag_call when tag is in schema."""

    class FakeBuilder:
        _schema_tag_names = {"div": "div"}

        def _bag_call(self, bag, name):
            return ("bag_call", bag, name)

    builder = FakeBuilder()
    bag = BuilderBag(builder=builder)
    result = bag.div
    assert result == ("bag_call", bag, "div")


def test_builder_bag_node_dispatches_to_builder_when_tag_known():
    """Decision 10: node.<tag>(...) routes to builder._command_on_node."""

    class FakeBuilder:
        _schema_tag_names = {"span": "span"}

        def _command_on_node(self, node, tag, node_position=None, node_value=None, **attrs):
            return ("cmd", node, tag, node_value, attrs)

    bag = BuilderBag()
    bag.set_item("root", None)
    node = bag.get_node("root")
    node._builder = FakeBuilder()
    node._handler = None
    result = node.span("hello", color="red")
    assert result == ("cmd", node, "span", "hello", {"color": "red"})


def test_builder_bag_node_unknown_tag_raises_attribute_error():
    """Tags not in the builder schema should not resolve."""

    class FakeBuilder:
        _schema_tag_names = {"div": "div"}

    bag = BuilderBag()
    bag.set_item("root", None)
    node = bag.get_node("root")
    node._builder = FakeBuilder()
    node._handler = None
    try:
        _ = node.unknown_tag
    except AttributeError:
        return
    raise AssertionError("expected AttributeError for tag not in schema")
