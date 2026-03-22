# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for pointer parsing, scanning, and node data resolution."""
from __future__ import annotations

from genro_bag import Bag
from genro_builders.builder_bag import BuilderBag, BuilderBagNode
from genro_builders.pointer import PointerInfo, is_pointer, parse_pointer, scan_for_pointers


# =============================================================================
# Tests for is_pointer
# =============================================================================


class TestIsPointer:
    """Tests for is_pointer detection."""

    def test_pointer_string(self):
        assert is_pointer("^user.name") is True

    def test_relative_pointer(self):
        assert is_pointer("^.name") is True

    def test_pointer_with_attr(self):
        assert is_pointer("^theme.btn?color") is True

    def test_normal_string(self):
        assert is_pointer("hello") is False

    def test_empty_string(self):
        assert is_pointer("") is False

    def test_non_string(self):
        assert is_pointer(42) is False
        assert is_pointer(None) is False
        assert is_pointer(["^x"]) is False


# =============================================================================
# Tests for parse_pointer
# =============================================================================


class TestParsePointer:
    """Tests for parse_pointer decomposition."""

    def test_absolute(self):
        info = parse_pointer("^alfa.beta")
        assert info.path == "alfa.beta"
        assert info.attr is None
        assert info.is_relative is False
        assert info.raw == "^alfa.beta"

    def test_relative(self):
        info = parse_pointer("^.name")
        assert info.path == ".name"
        assert info.attr is None
        assert info.is_relative is True

    def test_with_attr(self):
        info = parse_pointer("^alfa.beta?color")
        assert info.path == "alfa.beta"
        assert info.attr == "color"
        assert info.is_relative is False

    def test_relative_with_attr(self):
        info = parse_pointer("^.btn?size")
        assert info.path == ".btn"
        assert info.attr == "size"
        assert info.is_relative is True

    def test_simple_path(self):
        info = parse_pointer("^name")
        assert info.path == "name"
        assert info.attr is None
        assert info.is_relative is False


# =============================================================================
# Tests for scan_for_pointers
# =============================================================================


class TestScanForPointers:
    """Tests for scanning node value and attributes."""

    def test_pointer_in_value(self):
        bag = BuilderBag()
        node = bag.set_item("n", "^user.name")
        results = scan_for_pointers(node)

        assert len(results) == 1
        info, location = results[0]
        assert info.path == "user.name"
        assert location == "value"

    def test_pointer_in_attr(self):
        bag = BuilderBag()
        node = bag.set_item("n", "hello", color="^theme.color")
        results = scan_for_pointers(node)

        assert len(results) == 1
        info, location = results[0]
        assert info.path == "theme.color"
        assert location == "attr:color"

    def test_multiple_pointers(self):
        bag = BuilderBag()
        node = bag.set_item("n", "^data.value", color="^theme.color", size="^theme.size")
        results = scan_for_pointers(node)

        assert len(results) == 3
        locations = {loc for _, loc in results}
        assert "value" in locations
        assert "attr:color" in locations
        assert "attr:size" in locations

    def test_no_pointers(self):
        bag = BuilderBag()
        node = bag.set_item("n", "plain text", color="blue")
        results = scan_for_pointers(node)

        assert len(results) == 0

    def test_skip_private_attrs(self):
        bag = BuilderBag()
        node = bag.set_item("n", None, _internal="^secret")
        results = scan_for_pointers(node)

        assert len(results) == 0


# =============================================================================
# Tests for BuilderBagNode.get_relative_data
# =============================================================================


class TestGetRelativeData:
    """Tests for node-level data resolution."""

    def test_absolute_value(self):
        """Absolute path resolves directly."""
        data = Bag()
        data.set_item("user.name", "Giovanni")

        bag = BuilderBag()
        node = bag.set_item("n", None)

        result = node.get_relative_data(data, "user.name")
        assert result == "Giovanni"

    def test_absolute_attr(self):
        """Path with ?attr reads attribute from data node."""
        data = Bag()
        data.set_item("theme.btn", None, color="blue", size="large")

        bag = BuilderBag()
        node = bag.set_item("n", None)

        assert node.get_relative_data(data, "theme.btn?color") == "blue"
        assert node.get_relative_data(data, "theme.btn?size") == "large"

    def test_relative_path(self):
        """Relative path uses datapath from ancestor chain."""
        data = Bag()
        data.set_item("platform.services.api.port", 8080)

        # Build a tree with datapath attributes
        root = BuilderBag()
        root.set_backref()

        # Root level node with datapath
        platform_node = root.set_item("platform", BuilderBag(), datapath="platform")
        platform_bag = platform_node.value

        services_node = platform_bag.set_item("services", BuilderBag(), datapath=".services")
        services_bag = services_node.value

        api_node = services_bag.set_item("api", BuilderBag(), datapath=".api")
        api_bag = api_node.value

        target = api_bag.set_item("port_display", None)

        result = target.get_relative_data(data, ".port")
        assert result == 8080

    def test_missing_data_returns_none(self):
        """Missing path returns None."""
        data = Bag()
        bag = BuilderBag()
        node = bag.set_item("n", None)

        result = node.get_relative_data(data, "nonexistent")
        assert result is None

    def test_missing_attr_returns_none(self):
        """Missing attribute returns None."""
        data = Bag()
        data.set_item("x", "value")

        bag = BuilderBag()
        node = bag.set_item("n", None)

        result = node.get_relative_data(data, "x?nonexistent")
        assert result is None


# =============================================================================
# Tests for BuilderBagNode.set_relative_data
# =============================================================================


class TestSetRelativeData:
    """Tests for node-level data writing."""

    def test_set_absolute_value(self):
        """Set value at absolute path."""
        data = Bag()

        bag = BuilderBag()
        node = bag.set_item("n", None)

        node.set_relative_data(data, "user.name", "Giovanni")
        assert data["user.name"] == "Giovanni"

    def test_set_absolute_attr(self):
        """Set attribute at absolute path."""
        data = Bag()
        data.set_item("theme.btn", None)

        bag = BuilderBag()
        node = bag.set_item("n", None)

        node.set_relative_data(data, "theme.btn?color", "red")
        assert data.get_attr("theme.btn").get("color") == "red"

    def test_set_relative_value(self):
        """Set value at relative path using datapath chain."""
        data = Bag()

        root = BuilderBag()
        root.set_backref()

        section_node = root.set_item("section", BuilderBag(), datapath="config")
        section_bag = section_node.value

        target = section_bag.set_item("writer", None)

        target.set_relative_data(data, ".port", 3000)
        assert data["config.port"] == 3000
