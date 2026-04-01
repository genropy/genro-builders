# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for builder runtime pipeline — compile, render, reactivity."""
from __future__ import annotations

import pytest
from genro_bag import Bag

from genro_builders.builder import BagBuilderBase, element

from .helpers import TestBuilder, TestCompiler

# =============================================================================
# Subtree builder (for subtree-specific tests)
# =============================================================================


class SubtreeBuilder(BagBuilderBase):
    """Builder with wildcard container for subtree tests."""

    @element(sub_tags="*")
    def group(self): ...

    @element()
    def leaf(self): ...


SubtreeBuilder._compiler_class = TestCompiler


# =============================================================================
# Tests: Lifecycle
# =============================================================================


class TestAutonomousLifecycle:
    """Tests for basic builder lifecycle."""

    def test_populate_and_compile(self):
        """Populate source, compile, get output."""
        builder = TestBuilder()
        builder.source.heading("Hello")
        result = builder.build()

        assert result == builder.output
        assert "[heading:Hello]" in result

    def test_compile_returns_output(self):
        """compile() returns the rendered output."""
        builder = TestBuilder()
        builder.source.text("content")
        result = builder.build()

        assert result == builder.output
        assert "[text:content]" in result

    def test_no_renderer_or_compiler_raises(self):
        """Builder without renderer or compiler raises RuntimeError on build."""

        class NoCompBuilder(BagBuilderBase):
            @element()
            def div(self): ...

        builder = NoCompBuilder()
        builder.source.div()

        with pytest.raises(RuntimeError, match="no renderer or compiler"):
            builder.build()


# =============================================================================
# Tests: Pointer resolution
# =============================================================================


class TestAutonomousPointerResolution:
    """Tests for ^pointer resolution with standalone builder."""

    def test_pointer_in_value(self):
        """^pointer in node value is resolved from data."""
        builder = TestBuilder()
        builder.data["page.title"] = "Hello World"
        builder.source.heading("^page.title")
        builder.build()

        assert "Hello World" in builder.output

    def test_pointer_in_attr(self):
        """^pointer in node attribute is resolved from data."""
        builder = TestBuilder()
        builder.data["theme.color"] = "blue"
        builder.source.item(color="^theme.color")
        builder.build()

        assert "color=blue" in builder.output

    def test_multiple_pointers(self):
        """Multiple pointers in same source."""
        builder = TestBuilder()
        builder.data["title"] = "Title"
        builder.data["body"] = "Body text"
        builder.source.heading("^title")
        builder.source.text("^body")
        builder.build()

        assert "Title" in builder.output
        assert "Body text" in builder.output


# =============================================================================
# Tests: Reactivity
# =============================================================================


class TestAutonomousReactivity:
    """Tests for reactive data updates."""

    def test_data_change_updates_output(self):
        """Changing data after compile updates the output."""
        builder = TestBuilder()
        builder.data["title"] = "Original"
        builder.source.heading("^title")
        builder.build()

        assert "Original" in builder.output

        builder.data["title"] = "Updated"

        assert "Updated" in builder.output

    def test_data_change_partial_update(self):
        """Only nodes bound to changed data are updated."""
        builder = TestBuilder()
        builder.data["title"] = "Hello"
        builder.source.heading("^title")
        builder.source.text("static content")
        builder.build()

        assert "Hello" in builder.output
        assert "static content" in builder.output

        builder.data["title"] = "Changed"

        assert "Changed" in builder.output
        assert "static content" in builder.output


# =============================================================================
# Tests: Rebuild
# =============================================================================


class TestAutonomousRebuild:
    """Tests for full rebuild."""

    def test_rebuild_with_recipe(self):
        """rebuild() clears source and re-populates via callable."""
        builder = TestBuilder()
        builder.data["title"] = "v1"
        builder.source.heading("^title")
        builder.build()

        assert "v1" in builder.output

        builder.data["title"] = "v2"

        def new_main(source):
            source.heading("^title")

        builder.rebuild(main=new_main)

        assert "v2" in builder.output


# =============================================================================
# Tests: Data replacement
# =============================================================================


class TestAutonomousDataReplacement:
    """Tests for replacing the entire data Bag."""

    def test_replace_data_rebinds(self):
        """Setting data property replaces and rebinds."""
        builder = TestBuilder()
        builder.data["name"] = "Alice"
        builder.source.heading("^name")
        builder.build()

        assert "Alice" in builder.output

        new_data = Bag()
        new_data["name"] = "Bob"
        builder.data = new_data

        assert "Bob" in builder.output


# =============================================================================
# Tests: Component expansion
# =============================================================================


class TestAutonomousWithComponent:
    """Tests for component expansion with standalone builder."""

    def test_component_expanded_and_bound(self):
        """Components are expanded and their pointers are resolved."""
        builder = TestBuilder()
        builder.data["section.title"] = "My Section"
        builder.source.section(title="^section.title")
        builder.build()

        assert "My Section" in builder.output
        assert "default content" in builder.output


# =============================================================================
# Tests: Source delete
# =============================================================================


class TestAutonomousSourceDelete:
    """Tests for reactive source deletion."""

    def test_source_delete_updates_output(self):
        """Deleting a node from the source removes it from output."""
        builder = TestBuilder()
        builder.source.heading("Title")
        builder.source.text("Content")
        builder.build()

        assert "[heading:Title]" in builder.output
        assert "[text:Content]" in builder.output

        builder.source.del_item("text_0")
        assert "[text:Content]" not in builder.output
        assert "[heading:Title]" in builder.output

    def test_source_delete_with_pointer_cleanup(self):
        """Deleting a node with ^pointer cleans up the subscription map."""
        builder = TestBuilder()
        builder.data["title"] = "Hello"
        builder.source.heading("^title")
        builder.source.text("static")
        builder.build()

        assert "Hello" in builder.output
        assert len(builder._binding.subscription_map) > 0

        builder.source.del_item("heading_0")

        for entries in builder._binding.subscription_map.values():
            for compiled_entry in entries:
                node_path = compiled_entry.partition("?")[0]
                assert node_path != "heading_0"

        assert "Hello" not in builder.output
        assert "[text:static]" in builder.output

    def test_source_delete_subtree(self):
        """Deleting a node with children removes the entire subtree."""
        builder = SubtreeBuilder()
        inner = builder.source.group()
        inner.leaf("Child1")
        inner.leaf("Child2")
        builder.build()

        assert "Child1" in builder.output
        assert "Child2" in builder.output

        builder.source.del_item("group_0")

        assert "Child1" not in builder.output
        assert "Child2" not in builder.output


# =============================================================================
# Tests: Source insert
# =============================================================================


class TestAutonomousSourceInsert:
    """Tests for reactive source insertion."""

    def test_source_insert_updates_output(self):
        """Inserting a node into the source adds it to output."""
        builder = TestBuilder()
        builder.source.heading("Title")
        builder.build()

        assert "[heading:Title]" in builder.output
        assert "Extra" not in builder.output

        builder.source.text("Extra")

        assert "Extra" in builder.output
        assert "[heading:Title]" in builder.output

    def test_source_insert_with_pointer(self):
        """Inserted node with ^pointer gets bound to data."""
        builder = TestBuilder()
        builder.data["dynamic"] = "Resolved"
        builder.source.heading("Static")
        builder.build()

        assert "Resolved" not in builder.output

        builder.source.text("^dynamic")

        assert "Resolved" in builder.output

    def test_source_insert_at_position(self):
        """Inserted node appears at the correct position."""
        builder = TestBuilder()
        builder.source.heading("First")
        builder.source.heading("Third")
        builder.build()

        builder.source.text("Second", node_position=1)

        assert builder.output is not None
        first_pos = builder.output.index("First")
        second_pos = builder.output.index("Second")
        third_pos = builder.output.index("Third")
        assert first_pos < second_pos < third_pos


# =============================================================================
# Tests: Source update
# =============================================================================


class TestAutonomousSourceUpdate:
    """Tests for reactive source value/attribute updates."""

    def test_source_update_value(self):
        """Updating a node value in the source updates the output."""
        builder = TestBuilder()
        builder.source.heading("Original")
        builder.build()

        assert "Original" in builder.output

        builder.source.set_item("heading_0", "Modified")

        assert "Modified" in builder.output
        assert "Original" not in builder.output

    def test_source_update_attr(self):
        """Updating a node attribute in the source updates the output."""
        builder = TestBuilder()
        builder.source.item(color="red")
        builder.build()

        assert "color=red" in builder.output

        builder.source.set_attr("item_0", color="blue")

        assert "color=blue" in builder.output
        assert "color=red" not in builder.output

    def test_source_update_pointer_rebind(self):
        """Updating a static value to a ^pointer binds it to data."""
        builder = TestBuilder()
        builder.data["title"] = "Dynamic"
        builder.source.heading("static")
        builder.build()

        assert "static" in builder.output
        assert "Dynamic" not in builder.output

        builder.source.set_item("heading_0", "^title")

        assert "Dynamic" in builder.output

    def test_source_update_value_replaces_subtree(self):
        """Updating a node that had children replaces the entire subtree."""
        builder = SubtreeBuilder()
        builder.data["child_a"] = "A"
        builder.data["child_b"] = "B"
        inner = builder.source.group()
        inner.leaf("^child_a")
        inner.leaf("^child_b")
        builder.build()

        assert "A" in builder.output
        assert "B" in builder.output

        bindings_before = sum(
            len(v) for v in builder._binding.subscription_map.values()
        )

        builder.source.set_item("group_0", "replaced")

        assert "replaced" in builder.output
        assert "A" not in builder.output
        assert "B" not in builder.output

        bindings_after = sum(
            len(v) for v in builder._binding.subscription_map.values()
        )
        assert bindings_after < bindings_before


# =============================================================================
# Tests: Compiled observability
# =============================================================================


class TestAutonomousCompiledObservable:
    """Tests for compiled bag observability (live support)."""

    def test_compiled_bag_notifies_on_source_delete(self):
        """Subscriber on compiled bag receives delete events."""
        events = []
        builder = TestBuilder()
        builder.source.heading("Title")
        builder.source.text("Content")
        builder.build()

        builder.built.subscribe(
            "test", delete=lambda **kw: events.append(("del", kw.get("reason"))),
        )

        builder.source.del_item("text_0")

        assert len(events) == 1
        assert events[0] == ("del", "source")

    def test_compiled_bag_notifies_on_source_insert(self):
        """Subscriber on compiled bag receives insert events."""
        events = []
        builder = TestBuilder()
        builder.source.heading("Title")
        builder.build()

        builder.built.subscribe(
            "test", insert=lambda **kw: events.append(("ins", kw.get("reason"))),
        )

        builder.source.text("Extra")

        assert len(events) == 1
        assert events[0] == ("ins", "source")

    def test_compiled_bag_notifies_on_source_update_value(self):
        """Subscriber on compiled bag receives update events."""
        events = []
        builder = TestBuilder()
        builder.source.heading("Original")
        builder.build()

        builder.built.subscribe(
            "test", update=lambda **kw: events.append(("upd", kw.get("reason"))),
        )

        builder.source.set_item("heading_0", "Modified")

        assert len(events) >= 1
        assert any(e[1] == "source" for e in events)


# =============================================================================
# Tests: Map adequacy
# =============================================================================


class TestAutonomousMapAdequacy:
    """Tests that the subscription map adapts correctly."""

    def test_insert_adds_to_map(self):
        """Inserting a node with ^pointer adds an entry to the map."""
        builder = TestBuilder()
        builder.data["dynamic"] = "Resolved"
        builder.source.heading("static")
        builder.build()

        assert len(builder._binding.subscription_map) == 0

        builder.source.text("^dynamic")

        smap = builder._binding.subscription_map
        assert "dynamic" in smap
        assert any("text_0" in e for e in smap["dynamic"])

    def test_delete_removes_from_map(self):
        """Deleting a node with ^pointer removes its entry from the map."""
        builder = TestBuilder()
        builder.data["title"] = "T"
        builder.data["body"] = "B"
        builder.source.heading("^title")
        builder.source.text("^body")
        builder.build()

        smap = builder._binding.subscription_map
        assert "title" in smap
        assert "body" in smap

        builder.source.del_item("heading_0")

        smap = builder._binding.subscription_map
        assert "title" not in smap
        assert "body" in smap

    def test_update_value_replaces_map_entry(self):
        """Updating from static to ^pointer adds to the map."""
        builder = TestBuilder()
        builder.data["title"] = "Dynamic"
        builder.source.heading("static")
        builder.build()

        assert len(builder._binding.subscription_map) == 0

        builder.source.set_item("heading_0", "^title")

        smap = builder._binding.subscription_map
        assert "title" in smap
        assert "heading_0" in smap["title"]

    def test_update_pointer_to_static_removes_from_map(self):
        """Updating from ^pointer to static removes from the map."""
        builder = TestBuilder()
        builder.data["title"] = "Hello"
        builder.source.heading("^title")
        builder.build()

        assert "title" in builder._binding.subscription_map

        builder.source.set_item("heading_0", "static now")

        assert "title" not in builder._binding.subscription_map

    def test_update_attr_pointer_adds_to_map(self):
        """Updating attributes to include ^pointer adds to the map."""
        builder = TestBuilder()
        builder.data["theme.color"] = "blue"
        builder.source.item(color="red")
        builder.build()

        assert len(builder._binding.subscription_map) == 0

        builder.source.set_attr("item_0", color="^theme.color")

        smap = builder._binding.subscription_map
        assert "theme.color" in smap
        assert "item_0?color" in smap["theme.color"]

    def test_insert_reactive_after_map_registration(self):
        """After insert, data changes propagate to the new node."""
        builder = TestBuilder()
        builder.data["val"] = "first"
        builder.source.heading("static")
        builder.build()

        builder.source.text("^val")
        assert "first" in builder.output

        builder.data["val"] = "second"
        assert "second" in builder.output

