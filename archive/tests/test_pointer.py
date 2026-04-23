# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for pointer parsing, scanning, and node data resolution."""
from __future__ import annotations

from genro_bag import Bag
from genro_builders.builder_bag import BuilderBag, BuilderBagNode
from genro_builders.builder._binding import PointerInfo, is_pointer, parse_pointer, scan_for_pointers


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
