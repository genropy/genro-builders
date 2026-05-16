# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for level 2 of the bag/node layering (decision 12 v0.4.0).

Level 2 = ``BuilderSource``/``BuilderSourceNode``: a distinct subclass
of the level-1 base. It is scaffolding for the source role — an empty
extension point that already acts as a discriminating type.
"""
from __future__ import annotations

from genro_builders import (
    BuilderBag,
    BuilderBagNode,
    BuilderSource,
    BuilderSourceNode,
)


def test_source_bag_inherits_from_level_1():
    assert issubclass(BuilderSource, BuilderBag)
    assert issubclass(BuilderSourceNode, BuilderBagNode)


def test_source_bag_uses_source_node_class():
    bag = BuilderSource()
    bag.set_item("hello", "world")
    node = bag.get_node("hello")
    assert isinstance(node, BuilderSourceNode)


def test_source_bag_carries_level_1_slots():
    """Decision 10 + 12: level-2 bags inherit _builder/_handler from level 1."""
    sentinel_builder = object()
    sentinel_handler = object()
    src = BuilderSource(builder=sentinel_builder, handler=sentinel_handler)
    assert src._builder is sentinel_builder
    assert src._handler is sentinel_handler
