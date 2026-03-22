# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for BindingManager — reactive data binding."""
from __future__ import annotations

from genro_bag import Bag
from genro_builders.binding import BindingManager
from genro_builders.builder_bag import BuilderBag


class TestBindResolve:
    """Tests for initial pointer resolution during bind()."""

    def test_bind_resolves_value_pointer(self):
        """^pointer in node value is resolved from data."""
        data = Bag()
        data.set_item("user.name", "Giovanni")

        bag = BuilderBag()
        bag.set_item("greeting", "^user.name")

        manager = BindingManager()
        manager.bind(bag, data)

        node = bag.get_node("greeting")
        assert node.value == "Giovanni"

    def test_bind_resolves_attr_pointer(self):
        """^pointer in node attribute is resolved from data."""
        data = Bag()
        data.set_item("theme.color", "blue")

        bag = BuilderBag()
        bag.set_item("widget", None, color="^theme.color")

        manager = BindingManager()
        manager.bind(bag, data)

        node = bag.get_node("widget")
        assert node.attr.get("color") == "blue"

    def test_bind_resolves_attr_query(self):
        """^path?attr reads attribute from data node."""
        data = Bag()
        data.set_item("theme.btn", None, color="red", size="large")

        bag = BuilderBag()
        bag.set_item("widget", None, bg="^theme.btn?color")

        manager = BindingManager()
        manager.bind(bag, data)

        node = bag.get_node("widget")
        assert node.attr.get("bg") == "red"

    def test_bind_missing_data(self):
        """Missing data path resolves to None."""
        data = Bag()

        bag = BuilderBag()
        bag.set_item("n", "^nonexistent")

        manager = BindingManager()
        manager.bind(bag, data)

        node = bag.get_node("n")
        assert node.value is None


class TestSubscriptionMap:
    """Tests for subscription map structure."""

    def test_map_built_correctly(self):
        """Subscription map contains entries for all pointers."""
        data = Bag()
        data.set_item("a", 1)
        data.set_item("b", 2)

        bag = BuilderBag()
        bag.set_item("n1", "^a")
        bag.set_item("n2", "^b")

        manager = BindingManager()
        manager.bind(bag, data)

        smap = manager.subscription_map
        assert ("a", None) in smap
        assert ("b", None) in smap
        assert len(smap[("a", None)]) == 1
        assert len(smap[("b", None)]) == 1

    def test_multiple_nodes_same_pointer(self):
        """Multiple nodes bound to the same data path."""
        data = Bag()
        data.set_item("shared", "value")

        bag = BuilderBag()
        bag.set_item("n1", "^shared")
        bag.set_item("n2", "^shared")

        manager = BindingManager()
        manager.bind(bag, data)

        smap = manager.subscription_map
        assert len(smap[("shared", None)]) == 2

    def test_unbind_clears_map(self):
        """unbind() clears the subscription map."""
        data = Bag()
        data.set_item("x", 1)

        bag = BuilderBag()
        bag.set_item("n", "^x")

        manager = BindingManager()
        manager.bind(bag, data)
        assert len(manager.subscription_map) > 0

        manager.unbind()
        assert len(manager.subscription_map) == 0


class TestReactiveUpdate:
    """Tests for reactive node updates on data change."""

    def test_data_change_updates_value(self):
        """Changing data updates bound node value."""
        data = Bag()
        data.set_item("user.name", "Giovanni")

        bag = BuilderBag()
        bag.set_item("display", "^user.name")

        manager = BindingManager()
        manager.bind(bag, data)

        assert bag.get_node("display").value == "Giovanni"

        # Change data
        data.set_item("user.name", "Marco")

        assert bag.get_node("display").value == "Marco"

    def test_data_change_updates_attr(self):
        """Changing data updates bound node attribute."""
        data = Bag()
        data.set_item("theme.color", "blue")

        bag = BuilderBag()
        bag.set_item("widget", None, bg="^theme.color")

        manager = BindingManager()
        manager.bind(bag, data)

        assert bag.get_node("widget").attr.get("bg") == "blue"

        data.set_item("theme.color", "red")

        assert bag.get_node("widget").attr.get("bg") == "red"

    def test_data_change_calls_callback(self):
        """on_node_updated callback is called on data change."""
        updated_nodes = []

        data = Bag()
        data.set_item("x", 1)

        bag = BuilderBag()
        bag.set_item("n", "^x")

        manager = BindingManager(on_node_updated=lambda node: updated_nodes.append(node))
        manager.bind(bag, data)

        data.set_item("x", 2)

        assert len(updated_nodes) == 1
        assert updated_nodes[0].label == "n"

    def test_multiple_nodes_updated(self):
        """All nodes bound to changed path are updated."""
        data = Bag()
        data.set_item("val", "old")

        bag = BuilderBag()
        bag.set_item("n1", "^val")
        bag.set_item("n2", "^val")

        manager = BindingManager()
        manager.bind(bag, data)

        data.set_item("val", "new")

        assert bag.get_node("n1").value == "new"
        assert bag.get_node("n2").value == "new"

    def test_unrelated_change_no_update(self):
        """Changing unrelated data does not affect bound nodes."""
        data = Bag()
        data.set_item("a", "original")
        data.set_item("b", "other")

        bag = BuilderBag()
        bag.set_item("n", "^a")

        updated = []
        manager = BindingManager(on_node_updated=lambda node: updated.append(node))
        manager.bind(bag, data)

        data.set_item("b", "changed")

        assert len(updated) == 0
        assert bag.get_node("n").value == "original"


class TestNestedBag:
    """Tests for binding with nested Bag structures."""

    def test_bind_nested_pointers(self):
        """Pointers in nested Bags are resolved."""
        data = Bag()
        data.set_item("title", "Hello")
        data.set_item("color", "green")

        bag = BuilderBag()
        inner = Bag()
        inner.set_item("heading", "^title")
        inner.set_item("style", None, bg="^color")
        bag.set_item("container", inner)

        manager = BindingManager()
        manager.bind(bag, data)

        heading_node = inner.get_node("heading")
        assert heading_node.value == "Hello"

        style_node = inner.get_node("style")
        assert style_node.attr.get("bg") == "green"
