# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for reactive binding — pull model contract tests.

Pull model: BindingManager subscribes to any data change and signals
dirty via callback. No per-node dispatch, no per-node matching.
The callback receives the changed path for potential partial compile.
"""
from __future__ import annotations

from genro_bag import Bag

from genro_builders.builder._binding import (
    BindingManager,
    get_trigger_reason,
    scan_for_pointers,
)


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


class TestDataChangeCallback:
    """Any data change → callback fired with changed path."""

    def test_callback_fires_on_data_change(self):
        """Changing any data value fires the callback."""
        data = Bag()
        data.set_item("user.name", "Giovanni")

        changes = []
        bag = _make_built_bag({"display": "^user.name"})
        manager = BindingManager(on_data_changed=lambda path: changes.append(path))
        manager.subscribe(bag, data)

        data.set_item("user.name", "Marco")
        assert "user.name" in changes

    def test_callback_fires_for_unrelated_change(self):
        """In pull model, ANY data change fires the callback (no filtering)."""
        data = Bag()
        data.set_item("a", "original")
        data.set_item("b", "other")

        changes = []
        bag = _make_built_bag({"n": "^a"})
        manager = BindingManager(on_data_changed=lambda path: changes.append(path))
        manager.subscribe(bag, data)

        data.set_item("b", "changed")
        assert "b" in changes

    def test_no_callback_without_subscribe(self):
        """Without subscribe, no callback fires."""
        changes = []
        manager = BindingManager(on_data_changed=lambda path: changes.append(path))

        data = Bag()
        data.set_item("x", 1)
        assert len(changes) == 0


class TestReactiveNodesCollection:
    """BindingManager collects UI nodes with ^pointers."""

    def test_collects_nodes_with_value_pointer(self):
        """Nodes with ^pointer value are collected."""
        data = Bag()
        data.set_item("x", 1)
        bag = _make_built_bag({"n": "^x"})

        manager = BindingManager()
        manager.subscribe(bag, data)

        assert len(manager.reactive_nodes) == 1
        assert manager.reactive_nodes[0].label == "n"

    def test_collects_nodes_with_attr_pointer(self):
        """Nodes with ^pointer in attributes are collected."""
        data = Bag()
        data.set_item("color", "blue")
        bag = _make_built_bag({"w": (None, {"bg": "^color"})})

        manager = BindingManager()
        manager.subscribe(bag, data)

        assert len(manager.reactive_nodes) == 1

    def test_does_not_collect_static_nodes(self):
        """Nodes without ^pointers are not collected."""
        data = Bag()
        bag = _make_built_bag({"static": "hello"})

        manager = BindingManager()
        manager.subscribe(bag, data)

        assert len(manager.reactive_nodes) == 0


class TestPointerStaysFormal:
    """Data change does NOT modify the built node — pointer stays formal."""

    def test_pointer_stays_formal_after_data_change(self):
        data = Bag()
        data.set_item("user.name", "Giovanni")

        bag = _make_built_bag({"display": "^user.name"})
        manager = BindingManager()
        manager.subscribe(bag, data)

        assert bag.get_node("display").static_value == "^user.name"
        data.set_item("user.name", "Marco")
        assert bag.get_node("display").static_value == "^user.name"


class TestGetTriggerReason:
    """get_trigger_reason utility — 3-level path matching."""

    def test_exact_match(self):
        assert get_trigger_reason("user.name", "user.name") == "node"

    def test_container_match(self):
        assert get_trigger_reason("user.name", "user") == "container"

    def test_child_match(self):
        assert get_trigger_reason("user", "user.name") == "child"

    def test_no_match(self):
        assert get_trigger_reason("user.name", "config") is None

    def test_prefix_not_false_positive(self):
        assert get_trigger_reason("user", "username") is None


class TestUnbind:
    """unbind() stops all notifications."""

    def test_unbind_stops_notifications(self):
        data = Bag()
        data.set_item("x", 1)

        changes = []
        bag = _make_built_bag({"n": "^x"})
        manager = BindingManager(on_data_changed=lambda path: changes.append(path))
        manager.subscribe(bag, data)

        manager.unbind()
        data.set_item("x", 2)
        assert len(changes) == 0


class TestScanForPointers:
    """scan_for_pointers utility — pure function, no internals."""

    def test_scan_value_pointer(self):
        bag = Bag()
        bag.set_item("n", "^path")
        node = bag.get_node("n")
        pointers = scan_for_pointers(node)
        assert len(pointers) == 1
        assert pointers[0][0].path == "path"
        assert pointers[0][1] == "value"

    def test_scan_attr_pointer(self):
        bag = Bag()
        bag.set_item("n", None, color="^theme.color")
        node = bag.get_node("n")
        pointers = scan_for_pointers(node)
        assert len(pointers) == 1
        assert pointers[0][0].path == "theme.color"

    def test_scan_no_pointers(self):
        bag = Bag()
        bag.set_item("n", "static")
        node = bag.get_node("n")
        assert scan_for_pointers(node) == []
