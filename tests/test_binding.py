# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for BindingManager — flat subscription map and reactive updates."""
from __future__ import annotations

from genro_bag import Bag
from genro_builders.binding import BindingManager
from genro_builders.builder_bag import BuilderBag


def _setup_bound(data, bag, bindings):
    """Helper: register bindings, resolve initial values, subscribe.

    Args:
        data: The data Bag.
        bag: The compiled Bag (already populated).
        bindings: List of (data_key, compiled_entry) tuples.

    Returns:
        BindingManager instance, subscribed and ready.
    """
    manager = BindingManager()
    manager._compiled = bag  # set before resolve so _apply_to_compiled works
    for data_key, compiled_entry in bindings:
        manager.register(data_key, compiled_entry)
        resolved = manager._resolve_data_key(data, data_key)
        manager._apply_to_compiled(compiled_entry, resolved, trigger=False)
    manager.subscribe(bag, data)
    return manager


def _setup_bound_with_callback(data, bag, bindings, callback):
    """Like _setup_bound but with on_node_updated callback."""
    manager = BindingManager(on_node_updated=callback)
    manager._compiled = bag  # set before resolve so _apply_to_compiled works
    for data_key, compiled_entry in bindings:
        manager.register(data_key, compiled_entry)
        resolved = manager._resolve_data_key(data, data_key)
        manager._apply_to_compiled(compiled_entry, resolved, trigger=False)
    manager.subscribe(bag, data)
    return manager


class TestRegisterAndMap:
    """Tests for register() and flat subscription map structure."""

    def test_register_adds_entry(self):
        """register() adds entry to the map."""
        manager = BindingManager()
        manager.register("user.name", "heading_0")

        smap = manager.subscription_map
        assert "user.name" in smap
        assert smap["user.name"] == ["heading_0"]

    def test_register_multiple_same_key(self):
        """Multiple entries for same data_key."""
        manager = BindingManager()
        manager.register("val", "n1")
        manager.register("val", "n2")

        smap = manager.subscription_map
        assert len(smap["val"]) == 2

    def test_register_attr_pointer(self):
        """data_key with ?attr suffix and compiled_entry with ?attr suffix."""
        manager = BindingManager()
        manager.register("theme.btn?color", "widget_0?bg")

        smap = manager.subscription_map
        assert "theme.btn?color" in smap
        assert smap["theme.btn?color"] == ["widget_0?bg"]

    def test_unbind_clears_map(self):
        """unbind() clears the subscription map."""
        manager = BindingManager()
        manager.register("x", "n")

        data = Bag()
        bag = BuilderBag()
        bag.set_item("n", "val")
        manager.subscribe(bag, data)

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

        manager = _setup_bound(data, bag, [("user.name", "display")])

        assert bag.get_node("display").value == "Giovanni"

        data.set_item("user.name", "Marco")
        assert bag.get_node("display").value == "Marco"

    def test_data_change_updates_attr(self):
        """Changing data updates bound node attribute."""
        data = Bag()
        data.set_item("theme.color", "blue")

        bag = BuilderBag()
        bag.set_item("widget", None, bg="^theme.color")

        manager = _setup_bound(data, bag, [("theme.color", "widget?bg")])

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

        manager = _setup_bound_with_callback(
            data, bag, [("x", "n")],
            lambda node: updated_nodes.append(node),
        )

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

        manager = _setup_bound(data, bag, [("val", "n1"), ("val", "n2")])

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
        manager = _setup_bound_with_callback(
            data, bag, [("a", "n")],
            lambda node: updated.append(node),
        )

        data.set_item("b", "changed")
        assert len(updated) == 0
        assert bag.get_node("n").value == "original"


class TestRebind:
    """Tests for rebind with new data."""

    def test_rebind_updates_values(self):
        """rebind() re-resolves pointers against new data."""
        data1 = Bag()
        data1.set_item("name", "Alice")

        bag = BuilderBag()
        bag.set_item("display", "^name")

        manager = _setup_bound(data1, bag, [("name", "display")])
        assert bag.get_node("display").value == "Alice"

        data2 = Bag()
        data2.set_item("name", "Bob")
        manager.rebind(data2)

        assert bag.get_node("display").value == "Bob"

    def test_rebind_subscribes_to_new_data(self):
        """After rebind, changes to new data trigger updates."""
        data1 = Bag()
        data1.set_item("x", 1)

        bag = BuilderBag()
        bag.set_item("n", "^x")

        manager = _setup_bound(data1, bag, [("x", "n")])

        data2 = Bag()
        data2.set_item("x", 10)
        manager.rebind(data2)

        data2.set_item("x", 20)
        assert bag.get_node("n").value == 20


class TestAntiLoop:
    """Tests for anti-loop mechanism via _reason."""

    def test_reason_skips_originating_node(self):
        """Writing to data with _reason skips the originating compiled node."""
        data = Bag()
        data.set_item("val", "initial")

        bag = BuilderBag()
        bag.set_item("input_0", "^val")
        bag.set_item("label_0", "^val")

        updated = []
        manager = _setup_bound_with_callback(
            data, bag, [("val", "input_0"), ("val", "label_0")],
            lambda node: updated.append(node.label),
        )

        data.set_item("val", "from_input", _reason="input_0")

        assert "label_0" in updated
        assert "input_0" not in updated
        assert bag.get_node("label_0").value == "from_input"

    def test_no_reason_updates_all(self):
        """Without _reason, all bound nodes are updated."""
        data = Bag()
        data.set_item("val", "initial")

        bag = BuilderBag()
        bag.set_item("n1", "^val")
        bag.set_item("n2", "^val")

        updated = []
        manager = _setup_bound_with_callback(
            data, bag, [("val", "n1"), ("val", "n2")],
            lambda node: updated.append(node.label),
        )

        data.set_item("val", "changed")
        assert "n1" in updated
        assert "n2" in updated

    def test_reason_nonmatching_updates_all(self):
        """_reason that doesn't match any compiled path updates all nodes."""
        data = Bag()
        data.set_item("val", "initial")

        bag = BuilderBag()
        bag.set_item("n1", "^val")
        bag.set_item("n2", "^val")

        updated = []
        manager = _setup_bound_with_callback(
            data, bag, [("val", "n1"), ("val", "n2")],
            lambda node: updated.append(node.label),
        )

        data.set_item("val", "changed", _reason="nonexistent_node")
        assert "n1" in updated
        assert "n2" in updated


class TestUnbindPath:
    """Tests for unbind_path with flat map."""

    def test_unbind_path_removes_exact(self):
        """unbind_path removes entries matching exact path."""
        manager = BindingManager()
        manager.register("x", "n1")
        manager.register("y", "n2")

        manager.unbind_path("n1")

        smap = manager.subscription_map
        assert "x" not in smap
        assert "y" in smap

    def test_unbind_path_removes_children(self):
        """unbind_path removes entries for child nodes."""
        manager = BindingManager()
        manager.register("a", "parent.child1")
        manager.register("b", "parent.child2")

        manager.unbind_path("parent")

        smap = manager.subscription_map
        assert len(smap) == 0

    def test_unbind_path_keeps_unrelated(self):
        """unbind_path keeps entries not under the given path."""
        manager = BindingManager()
        manager.register("a", "parent.child1")
        manager.register("b", "other")

        manager.unbind_path("parent")

        smap = manager.subscription_map
        assert "a" not in smap
        assert "b" in smap
        assert smap["b"] == ["other"]
