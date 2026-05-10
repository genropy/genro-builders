# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for level 2 of the bag/node layering (decision 12).

Level 2 = ``BuilderSourceBag``/``BuilderSourceBagNode`` and
``BuilderBuiltBag``/``BuilderBuiltBagNode``: distinct subclasses of
the level-1 base. They are scaffolding during fase 2.3 — empty
extension points that already act as discriminating types.
"""
from __future__ import annotations

from genro_builders import (
    BuilderBag,
    BuilderBagNode,
    BuilderBuiltBag,
    BuilderBuiltBagNode,
    BuilderSourceBag,
    BuilderSourceBagNode,
)


def test_source_bag_inherits_from_level_1():
    assert issubclass(BuilderSourceBag, BuilderBag)
    assert issubclass(BuilderSourceBagNode, BuilderBagNode)


def test_built_bag_inherits_from_level_1():
    assert issubclass(BuilderBuiltBag, BuilderBag)
    assert issubclass(BuilderBuiltBagNode, BuilderBagNode)


def test_source_and_built_are_distinct_types():
    """Decision 12: types discriminate the two phases."""
    assert BuilderSourceBag is not BuilderBuiltBag
    assert BuilderSourceBagNode is not BuilderBuiltBagNode
    assert not issubclass(BuilderSourceBag, BuilderBuiltBag)
    assert not issubclass(BuilderBuiltBag, BuilderSourceBag)


def test_source_bag_uses_source_node_class():
    bag = BuilderSourceBag()
    bag.set_item("hello", "world")
    node = bag.get_node("hello")
    assert isinstance(node, BuilderSourceBagNode)


def test_built_bag_uses_built_node_class():
    bag = BuilderBuiltBag()
    bag.set_item("hello", "world")
    node = bag.get_node("hello")
    assert isinstance(node, BuilderBuiltBagNode)


def test_level_2_bags_carry_level_1_slots():
    """Decision 10 + 12: level-2 bags inherit _builder/_handler from level 1."""
    sentinel_builder = object()
    sentinel_handler = object()
    src = BuilderSourceBag(builder=sentinel_builder, handler=sentinel_handler)
    built = BuilderBuiltBag(builder=sentinel_builder, handler=sentinel_handler)
    assert src._builder is sentinel_builder
    assert src._handler is sentinel_handler
    assert built._builder is sentinel_builder
    assert built._handler is sentinel_handler
