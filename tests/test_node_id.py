# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for node_id feature: unique node identification and lookup."""
from __future__ import annotations

import pytest

from genro_builders.builder import BagBuilderBase, element


class SimpleBuilder(BagBuilderBase):
    """Builder for node_id tests."""

    @element(sub_tags="*")
    def container(self): ...

    @element(sub_tags="")
    def item(self): ...

    @element(sub_tags="item")
    def group(self): ...


class TestNodeId:
    """Tests for node_id assignment and lookup."""

    def test_node_id_assigned_as_attribute(self):
        builder = SimpleBuilder()
        builder.source.item("hello", node_id="my_item")
        node = builder.node_by_id("my_item")
        assert node.attr.get("node_id") == "my_item"

    def test_node_by_id_returns_correct_node(self):
        builder = SimpleBuilder()
        builder.source.item("first", node_id="a")
        builder.source.item("second", node_id="b")
        assert builder.node_by_id("a").static_value == "first"
        assert builder.node_by_id("b").static_value == "second"

    def test_node_by_id_on_containers(self):
        builder = SimpleBuilder()
        c = builder.source.container(node_id="root")
        c.item("child1", node_id="c1")
        c.item("child2", node_id="c2")
        assert builder.node_by_id("root").node_tag == "container"
        assert builder.node_by_id("c1").static_value == "child1"
        assert builder.node_by_id("c2").static_value == "child2"

    def test_duplicate_node_id_raises(self):
        builder = SimpleBuilder()
        builder.source.item("first", node_id="dup")
        with pytest.raises(ValueError, match="Duplicate node_id 'dup'"):
            builder.source.item("second", node_id="dup")

    def test_node_by_id_missing_raises(self):
        builder = SimpleBuilder()
        with pytest.raises(KeyError, match="No node with node_id 'missing'"):
            builder.node_by_id("missing")

    def test_node_id_not_required(self):
        builder = SimpleBuilder()
        builder.source.item("no id")
        assert builder._node_id_map == {}

    def test_clear_source_resets_node_id_map(self):
        builder = SimpleBuilder()
        builder.source.item("hello", node_id="my_item")
        assert builder.node_by_id("my_item") is not None
        builder._clear_source()
        with pytest.raises(KeyError):
            builder.node_by_id("my_item")

    def test_node_id_with_nested_groups(self):
        builder = SimpleBuilder()
        g = builder.source.group(node_id="grp")
        g.item("inside", node_id="inner")
        assert builder.node_by_id("grp").node_tag == "group"
        assert builder.node_by_id("inner").static_value == "inside"
