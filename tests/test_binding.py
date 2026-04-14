# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for reactive binding — end-to-end contract tests.

Tests verify the public contract: data change → affected nodes notified.
No internal structure (subscription map, registry) is inspected.
"""
from __future__ import annotations

from genro_bag import Bag

from genro_builders.builder._binding import BindingManager, scan_for_pointers


def _make_built_bag(items: dict) -> Bag:
    """Create a built-like Bag with nodes containing ^pointer values."""
    bag = Bag()
    bag.set_backref()
    for label, value in items.items():
        if isinstance(value, tuple):
            bag.set_item(label, value[0], **value[1])
        else:
            bag.set_item(label, value)
    return bag


def _setup_reactive(data: Bag, items: dict, callback=None) -> BindingManager:
    """Create a BindingManager, build a bag with ^pointers, subscribe."""
    bag = _make_built_bag(items)
    manager = BindingManager(on_node_updated=callback)
    manager.subscribe(bag, data)
    return manager


class TestReactiveNotification:
    """Data change → callback notified for affected nodes."""

    def test_data_change_notifies_node_with_pointer(self):
        """Changing data notifies node whose value is ^pointer."""
        data = Bag()
        data.set_item("user.name", "Giovanni")

        updated = []
        _setup_reactive(data, {"display": "^user.name"},
                        callback=lambda node: updated.append(node.label))

        data.set_item("user.name", "Marco")
        assert "display" in updated

    def test_data_change_notifies_node_with_attr_pointer(self):
        """Changing data notifies node whose attribute is ^pointer."""
        data = Bag()
        data.set_item("theme.color", "blue")

        updated = []
        _setup_reactive(data, {"widget": (None, {"bg": "^theme.color"})},
                        callback=lambda node: updated.append(node.label))

        data.set_item("theme.color", "red")
        assert "widget" in updated

    def test_multiple_nodes_notified(self):
        """All nodes with ^pointer to changed path are notified."""
        data = Bag()
        data.set_item("val", "old")

        updated = []
        _setup_reactive(data, {"n1": "^val", "n2": "^val"},
                        callback=lambda node: updated.append(node.label))

        data.set_item("val", "new")
        assert "n1" in updated
        assert "n2" in updated

    def test_unrelated_change_no_notification(self):
        """Changing unrelated data does not trigger notification."""
        data = Bag()
        data.set_item("a", "original")
        data.set_item("b", "other")

        updated = []
        _setup_reactive(data, {"n": "^a"},
                        callback=lambda node: updated.append(node))

        data.set_item("b", "changed")
        assert len(updated) == 0

    def test_pointer_stays_formal_after_data_change(self):
        """Data change does NOT modify the built node — pointer stays formal."""
        data = Bag()
        data.set_item("user.name", "Giovanni")

        bag = _make_built_bag({"display": "^user.name"})
        manager = BindingManager()
        manager.subscribe(bag, data)

        assert bag.get_node("display").static_value == "^user.name"
        data.set_item("user.name", "Marco")
        assert bag.get_node("display").static_value == "^user.name"


class TestThreeLevelPropagation:
    """3-level trigger: node (exact), container (ancestor), child (descendant)."""

    def test_exact_match(self):
        """Exact path match triggers notification."""
        data = Bag()
        data.set_item("user.name", "Alice")

        updated = []
        _setup_reactive(data, {"display": "^user.name"},
                        callback=lambda node: updated.append(node.label))

        data.set_item("user.name", "Bob")
        assert "display" in updated

    def test_ancestor_changed(self):
        """Ancestor change triggers notification (container level)."""
        data = Bag()
        data.set_item("user.name", "Alice")

        updated = []
        _setup_reactive(data, {"display": "^user.name"},
                        callback=lambda node: updated.append(node.label))

        new_user = Bag()
        new_user["name"] = "Bob"
        data.set_item("user", new_user)
        assert "display" in updated

    def test_descendant_changed(self):
        """Descendant change triggers notification (child level)."""
        data = Bag()
        data.set_item("user.name", "Alice")

        updated = []
        _setup_reactive(data, {"display": "^user"},
                        callback=lambda node: updated.append(node.label))

        data.set_item("user.name", "Bob")
        assert "display" in updated

    def test_unrelated_path_no_trigger(self):
        """Unrelated path change does not trigger notification."""
        data = Bag()
        data.set_item("user.name", "Alice")
        data.set_item("config.theme", "dark")

        updated = []
        _setup_reactive(data, {"display": "^user.name"},
                        callback=lambda node: updated.append(node.label))

        data.set_item("config.theme", "light")
        assert len(updated) == 0

    def test_get_trigger_reason_logic(self):
        """Direct test of 3-level matching logic."""
        manager = BindingManager()
        assert manager._get_trigger_reason("user.name", "user.name") == "node"
        assert manager._get_trigger_reason("user.name", "user") == "container"
        assert manager._get_trigger_reason("user", "user.name") == "child"
        assert manager._get_trigger_reason("user.name", "config") is None
        assert manager._get_trigger_reason("user", "username") is None


class TestAntiLoop:
    """Anti-loop: _reason prevents re-notification of originating node."""

    def test_reason_skips_originating_node(self):
        """Writing to data with _reason=node skips that node."""
        data = Bag()
        data.set_item("val", "initial")

        bag = _make_built_bag({"input_0": "^val", "label_0": "^val"})
        updated = []
        manager = BindingManager(
            on_node_updated=lambda node: updated.append(node.label),
        )
        manager.subscribe(bag, data)

        input_node = bag.get_node("input_0")
        data.set_item("val", "from_input", _reason=input_node)

        assert "label_0" in updated
        assert "input_0" not in updated

    def test_no_reason_updates_all(self):
        """Without _reason, all nodes with matching ^pointer are notified."""
        data = Bag()
        data.set_item("val", "initial")

        updated = []
        _setup_reactive(data, {"n1": "^val", "n2": "^val"},
                        callback=lambda node: updated.append(node.label))

        data.set_item("val", "changed")
        assert "n1" in updated
        assert "n2" in updated


class TestUnbind:
    """unbind() stops all notifications."""

    def test_unbind_stops_notifications(self):
        """After unbind, data changes do not trigger notifications."""
        data = Bag()
        data.set_item("x", 1)

        updated = []
        manager = _setup_reactive(data, {"n": "^x"},
                                  callback=lambda node: updated.append(node.label))

        manager.unbind()
        data.set_item("x", 2)
        assert len(updated) == 0


class TestScanForPointers:
    """scan_for_pointers utility — pure function, no internals."""

    def test_scan_value_pointer(self):
        """Detects ^pointer in node value."""
        bag = Bag()
        bag.set_item("n", "^path")
        node = bag.get_node("n")
        pointers = scan_for_pointers(node)
        assert len(pointers) == 1
        assert pointers[0][0].path == "path"
        assert pointers[0][1] == "value"

    def test_scan_attr_pointer(self):
        """Detects ^pointer in node attributes."""
        bag = Bag()
        bag.set_item("n", None, color="^theme.color")
        node = bag.get_node("n")
        pointers = scan_for_pointers(node)
        assert len(pointers) == 1
        assert pointers[0][0].path == "theme.color"

    def test_scan_no_pointers(self):
        """No pointers returns empty list."""
        bag = Bag()
        bag.set_item("n", "static")
        node = bag.get_node("n")
        assert scan_for_pointers(node) == []
