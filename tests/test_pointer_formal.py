# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for formal pointers — built Bag preserves ^pointer strings.

After build, the built Bag contains ^pointer strings (not resolved values).
Resolution happens just-in-time during render/compile via _resolve_node.
The built Bag is never modified by reactive updates.
"""
from __future__ import annotations

from genro_bag import Bag

from tests.helpers import TestBuilder


class TestBuiltPreservesPointers:
    """Built Bag keeps ^pointer strings after build."""

    def test_pointer_in_value_preserved(self):
        """Built node value keeps ^pointer string."""
        builder = TestBuilder()
        builder.data["title"] = "Hello"
        builder.source.heading("^title")
        builder.build()

        node = builder.built.get_node("heading_0")
        assert node.static_value == "^title"

    def test_pointer_in_attr_preserved(self):
        """Built node attribute keeps ^pointer string."""
        builder = TestBuilder()
        builder.data["theme.color"] = "blue"
        builder.source.item(color="^theme.color")
        builder.build()

        node = builder.built.get_node("item_0")
        assert node.attr.get("color") == "^theme.color"

    def test_multiple_pointers_preserved(self):
        """Multiple pointer nodes all keep their strings."""
        builder = TestBuilder()
        builder.data["title"] = "Title"
        builder.data["body"] = "Body"
        builder.source.heading("^title")
        builder.source.text("^body")
        builder.build()

        assert builder.built.get_node("heading_0").static_value == "^title"
        assert builder.built.get_node("text_0").static_value == "^body"

    def test_static_value_not_affected(self):
        """Non-pointer values are stored as-is in built."""
        builder = TestBuilder()
        builder.source.heading("Static Title")
        builder.build()

        node = builder.built.get_node("heading_0")
        assert node.static_value == "Static Title"


class TestRenderResolvesPointers:
    """Render produces resolved values via just-in-time resolution."""

    def test_render_resolves_value_pointer(self):
        """Render output contains the resolved value, not ^pointer."""
        builder = TestBuilder()
        builder.data["title"] = "Hello World"
        builder.source.heading("^title")
        builder.build()

        output = builder.render()
        assert "Hello World" in output
        assert "^title" not in output

    def test_render_resolves_attr_pointer(self):
        """Render output contains resolved attribute value."""
        builder = TestBuilder()
        builder.data["theme.color"] = "blue"
        builder.source.item(color="^theme.color")
        builder.build()

        output = builder.render()
        assert "blue" in output

    def test_render_with_none_data(self):
        """Pointer to missing data resolves to None at render."""
        builder = TestBuilder()
        builder.source.heading("^nonexistent")
        builder.build()

        output = builder.render()
        assert "^nonexistent" not in output


class TestBuiltImmutableAfterDataChange:
    """Built Bag is NOT modified when data changes."""

    def test_built_unchanged_after_data_change(self):
        """After data change, built still has ^pointer."""
        builder = TestBuilder()
        builder.data["title"] = "Original"
        builder.source.heading("^title")
        builder.build()
        builder.subscribe()

        builder.data["title"] = "Updated"

        # Built still has the pointer
        node = builder.built.get_node("heading_0")
        assert node.static_value == "^title"

    def test_render_reflects_updated_data(self):
        """After data change + re-render, output has the new value."""
        builder = TestBuilder()
        builder.data["title"] = "Original"
        builder.source.heading("^title")
        builder.build()
        builder.subscribe()

        assert "Original" in builder.output

        builder.data["title"] = "Updated"
        assert "Updated" in builder.output

    def test_attr_pointer_unchanged_after_data_change(self):
        """Built attribute keeps ^pointer after data change."""
        builder = TestBuilder()
        builder.data["color"] = "blue"
        builder.source.item(color="^color")
        builder.build()
        builder.subscribe()

        builder.data["color"] = "red"

        node = builder.built.get_node("item_0")
        assert node.attr.get("color") == "^color"
