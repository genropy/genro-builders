# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for BindingManager — flat subscription map and reactive notifications.

The BindingManager does NOT modify the built Bag. It only signals re-render
via the on_node_updated callback when data changes.
"""
from __future__ import annotations

from genro_bag import Bag

from genro_builders.builder._binding import BindingManager
from genro_builders.builder_bag import BuilderBag


def _setup_bound(data, bag, bindings, callback=None):
    """Helper: register bindings, subscribe.

    Args:
        data: The data Bag.
        bag: The built Bag (already populated).
        bindings: List of (data_key, built_entry) tuples.
        callback: Optional on_node_updated callback.

    Returns:
        BindingManager instance, subscribed and ready.
    """
    manager = BindingManager(on_node_updated=callback)
    for data_key, built_entry in bindings:
        manager.register(data_key, built_entry)
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
        """data_key with ?attr suffix and built_entry with ?attr suffix."""
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


class TestReactiveNotification:
    """Tests for reactive notifications on data change.

    The BindingManager does NOT write values to the built Bag.
    It calls on_node_updated to signal that a re-render is needed.
    """

    def test_data_change_notifies_bound_node(self):
        """Changing data calls on_node_updated for bound node."""
        data = Bag()
        data.set_item("user.name", "Giovanni")

        bag = BuilderBag()
        bag.set_item("display", "^user.name")

        updated = []
        _setup_bound(data, bag, [("user.name", "display")],
                     callback=lambda node: updated.append(node.label))

        data.set_item("user.name", "Marco")
        assert "display" in updated

    def test_data_change_preserves_pointer_in_built(self):
        """Data change does NOT modify the built node — pointer stays."""
        data = Bag()
        data.set_item("user.name", "Giovanni")

        bag = BuilderBag()
        bag.set_item("display", "^user.name")

        _setup_bound(data, bag, [("user.name", "display")])

        # Built node keeps the pointer string
        assert bag.get_node("display").static_value == "^user.name"

        data.set_item("user.name", "Marco")
        # Still pointer, not resolved value
        assert bag.get_node("display").static_value == "^user.name"

    def test_data_change_notifies_attr_binding(self):
        """Changing data notifies node with attribute binding."""
        data = Bag()
        data.set_item("theme.color", "blue")

        bag = BuilderBag()
        bag.set_item("widget", None, bg="^theme.color")

        updated = []
        _setup_bound(data, bag, [("theme.color", "widget?bg")],
                     callback=lambda node: updated.append(node.label))

        data.set_item("theme.color", "red")
        assert "widget" in updated
        # Attr keeps the pointer
        assert bag.get_node("widget").attr.get("bg") == "^theme.color"

    def test_data_change_calls_callback(self):
        """on_node_updated callback receives the correct node."""
        updated_nodes = []

        data = Bag()
        data.set_item("x", 1)

        bag = BuilderBag()
        bag.set_item("n", "^x")

        _setup_bound(data, bag, [("x", "n")],
                     callback=lambda node: updated_nodes.append(node))

        data.set_item("x", 2)
        assert len(updated_nodes) == 1
        assert updated_nodes[0].label == "n"

    def test_multiple_nodes_notified(self):
        """All nodes bound to changed path are notified."""
        data = Bag()
        data.set_item("val", "old")

        bag = BuilderBag()
        bag.set_item("n1", "^val")
        bag.set_item("n2", "^val")

        updated = []
        _setup_bound(data, bag, [("val", "n1"), ("val", "n2")],
                     callback=lambda node: updated.append(node.label))

        data.set_item("val", "new")
        assert "n1" in updated
        assert "n2" in updated

    def test_unrelated_change_no_notification(self):
        """Changing unrelated data does not trigger notification."""
        data = Bag()
        data.set_item("a", "original")
        data.set_item("b", "other")

        bag = BuilderBag()
        bag.set_item("n", "^a")

        updated = []
        _setup_bound(data, bag, [("a", "n")],
                     callback=lambda node: updated.append(node))

        data.set_item("b", "changed")
        assert len(updated) == 0


class TestRebind:
    """Tests for rebind with new data."""

    def test_rebind_notifies_all_bound_nodes(self):
        """rebind() triggers notification for all bound nodes."""
        data1 = Bag()
        data1.set_item("name", "Alice")

        bag = BuilderBag()
        bag.set_item("display", "^name")

        updated = []
        manager = _setup_bound(data1, bag, [("name", "display")],
                               callback=lambda node: updated.append(node.label))

        data2 = Bag()
        data2.set_item("name", "Bob")
        manager.rebind(data2)

        assert "display" in updated

    def test_rebind_subscribes_to_new_data(self):
        """After rebind, changes to new data trigger notifications."""
        data1 = Bag()
        data1.set_item("x", 1)

        bag = BuilderBag()
        bag.set_item("n", "^x")

        updated = []
        manager = _setup_bound(data1, bag, [("x", "n")],
                               callback=lambda node: updated.append(node.label))

        data2 = Bag()
        data2.set_item("x", 10)
        manager.rebind(data2)
        updated.clear()

        data2.set_item("x", 20)
        assert "n" in updated


class TestAntiLoop:
    """Tests for anti-loop mechanism via _reason."""

    def test_reason_skips_originating_node(self):
        """Writing to data with _reason skips the originating built node."""
        data = Bag()
        data.set_item("val", "initial")

        bag = BuilderBag()
        bag.set_item("input_0", "^val")
        bag.set_item("label_0", "^val")

        updated = []
        _setup_bound(data, bag, [("val", "input_0"), ("val", "label_0")],
                     callback=lambda node: updated.append(node.label))

        data.set_item("val", "from_input", _reason="input_0")

        assert "label_0" in updated
        assert "input_0" not in updated

    def test_no_reason_updates_all(self):
        """Without _reason, all bound nodes are notified."""
        data = Bag()
        data.set_item("val", "initial")

        bag = BuilderBag()
        bag.set_item("n1", "^val")
        bag.set_item("n2", "^val")

        updated = []
        _setup_bound(data, bag, [("val", "n1"), ("val", "n2")],
                     callback=lambda node: updated.append(node.label))

        data.set_item("val", "changed")
        assert "n1" in updated
        assert "n2" in updated

    def test_reason_nonmatching_updates_all(self):
        """_reason that doesn't match any built path notifies all nodes."""
        data = Bag()
        data.set_item("val", "initial")

        bag = BuilderBag()
        bag.set_item("n1", "^val")
        bag.set_item("n2", "^val")

        updated = []
        _setup_bound(data, bag, [("val", "n1"), ("val", "n2")],
                     callback=lambda node: updated.append(node.label))

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


class TestThreeLevelPropagation:
    """Tests for 3-level trigger reason: node, container, child."""

    def test_node_exact_match(self):
        """Exact path match triggers notification (node level)."""
        data = Bag()
        data.set_item("user.name", "Alice")

        bag = BuilderBag()
        bag.set_item("display", "^user.name")

        updated = []
        _setup_bound(data, bag, [("user.name", "display")],
                     callback=lambda node: updated.append(node.label))

        data.set_item("user.name", "Bob")
        assert "display" in updated

    def test_container_ancestor_changed(self):
        """Ancestor change triggers notification (container level).

        Watching 'user.name', changing 'user' (replace entire subtree).
        """
        data = Bag()
        data.set_item("user.name", "Alice")

        bag = BuilderBag()
        bag.set_item("display", "^user.name")

        updated = []
        _setup_bound(data, bag, [("user.name", "display")],
                     callback=lambda node: updated.append(node.label))

        # Replace entire 'user' — ancestor of 'user.name'
        new_user = Bag()
        new_user["name"] = "Bob"
        data.set_item("user", new_user)
        assert "display" in updated

    def test_child_descendant_changed(self):
        """Descendant change triggers notification (child level).

        Watching 'user', changing 'user.name' (a child path).
        """
        data = Bag()
        data.set_item("user.name", "Alice")

        bag = BuilderBag()
        bag.set_item("display", "^user")

        updated = []
        _setup_bound(data, bag, [("user", "display")],
                     callback=lambda node: updated.append(node.label))

        data.set_item("user.name", "Bob")
        assert "display" in updated

    def test_unrelated_path_no_trigger(self):
        """Unrelated path change does not trigger notification."""
        data = Bag()
        data.set_item("user.name", "Alice")
        data.set_item("config.theme", "dark")

        bag = BuilderBag()
        bag.set_item("display", "^user.name")

        updated = []
        _setup_bound(data, bag, [("user.name", "display")],
                     callback=lambda node: updated.append(node.label))

        data.set_item("config.theme", "light")
        assert len(updated) == 0

    def test_get_trigger_reason_method(self):
        """Direct test of _get_trigger_reason logic."""
        manager = BindingManager()
        assert manager._get_trigger_reason("user.name", "user.name") == "node"
        assert manager._get_trigger_reason("user.name", "user") == "container"
        assert manager._get_trigger_reason("user", "user.name") == "child"
        assert manager._get_trigger_reason("user.name", "config") is None
        assert manager._get_trigger_reason("user", "username") is None
