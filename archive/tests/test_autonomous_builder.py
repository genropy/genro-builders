# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for builder runtime pipeline — build, render, subscribe, reactivity."""
from __future__ import annotations

import pytest
from genro_bag import Bag

from genro_builders.builder import BagBuilderBase, element

from .helpers import TestBuilder, TestRenderer

# =============================================================================
# Subtree builder (for subtree-specific tests)
# =============================================================================


class SubtreeBuilder(BagBuilderBase):
    """Builder with wildcard container for subtree tests."""

    _renderers = {"test": TestRenderer}

    @element(sub_tags="*")
    def group(self): ...

    @element()
    def leaf(self): ...


# =============================================================================
# Tests: Lifecycle
# =============================================================================


class TestAutonomousLifecycle:
    """Tests for basic builder lifecycle."""

    def test_populate_and_render(self):
        """Populate source, build, render output."""
        builder = TestBuilder()
        builder.source.heading("Hello")
        builder.build()
        result = builder.render()

        assert "[heading:Hello]" in result

    def test_build_then_render(self):
        """build() materializes, render() produces output."""
        builder = TestBuilder()
        builder.source.text("content")
        builder.build()
        result = builder.render()

        assert "[text:content]" in result

    def test_no_renderer_or_compiler_raises(self):
        """Builder without renderer or compiler raises RuntimeError on render."""

        class NoCompBuilder(BagBuilderBase):
            @element()
            def div(self): ...

        builder = NoCompBuilder()
        builder.source.div()
        builder.build()

        with pytest.raises(RuntimeError, match="no renderer registered"):
            builder.render()


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

        assert "Hello World" in builder.render()

    def test_pointer_in_attr(self):
        """^pointer in node attribute is resolved from data."""
        builder = TestBuilder()
        builder.data["theme.color"] = "blue"
        builder.source.item(color="^theme.color")
        builder.build()

        assert "color=blue" in builder.render()

    def test_multiple_pointers(self):
        """Multiple pointers in same source."""
        builder = TestBuilder()
        builder.data["title"] = "Title"
        builder.data["body"] = "Body text"
        builder.source.heading("^title")
        builder.source.text("^body")
        builder.build()

        output = builder.render()
        assert "Title" in output
        assert "Body text" in output


# =============================================================================
# Tests: Reactivity (requires subscribe)
# =============================================================================


class TestAutonomousReactivity:
    """Tests for reactive data updates."""

    def test_data_change_updates_output(self):
        """Changing data after subscribe updates the output."""
        builder = TestBuilder()
        builder.data["title"] = "Original"
        builder.source.heading("^title")
        builder.build()
        builder.subscribe()

        assert "Original" in builder.render()

        builder.data["title"] = "Updated"

        assert "Updated" in builder.render()

    def test_data_change_partial_update(self):
        """Only nodes bound to changed data are updated."""
        builder = TestBuilder()
        builder.data["title"] = "Hello"
        builder.source.heading("^title")
        builder.source.text("static content")
        builder.build()
        builder.subscribe()

        assert "Hello" in builder.render()
        assert "static content" in builder.render()

        builder.data["title"] = "Changed"

        assert "Changed" in builder.render()
        assert "static content" in builder.render()


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
        builder.subscribe()

        assert "v1" in builder.render()

        builder.data["title"] = "v2"

        def new_main(source):
            source.heading("^title")

        builder.rebuild(main=new_main)
        builder.subscribe()

        assert "v2" in builder.render()


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
        builder.subscribe()

        assert "Alice" in builder.render()

        new_data = Bag()
        new_data["name"] = "Bob"
        builder.data = new_data

        assert "Bob" in builder.render()


# =============================================================================
# Tests: Component expansion
# =============================================================================


# =============================================================================
# Tests: Source delete (requires subscribe for reactivity)
# =============================================================================


class TestAutonomousSourceDelete:
    """Tests for reactive source deletion."""

    def test_source_delete_updates_output(self):
        """Deleting a node from the source removes it from output."""
        builder = TestBuilder()
        builder.source.heading("Title")
        builder.source.text("Content")
        builder.build()
        builder.subscribe()

        assert "[heading:Title]" in builder.render()
        assert "[text:Content]" in builder.render()

        builder.source.del_item("text_0")
        assert "[text:Content]" not in builder.render()
        assert "[heading:Title]" in builder.render()

    def test_source_delete_with_pointer_cleanup(self):
        """Deleting a node with ^pointer removes it from output."""
        builder = TestBuilder()
        builder.data["title"] = "Hello"
        builder.source.heading("^title")
        builder.source.text("static")
        builder.build()
        builder.subscribe()

        assert "Hello" in builder.render()

        builder.source.del_item("heading_0")

        assert "Hello" not in builder.render()
        assert "[text:static]" in builder.render()

    def test_source_delete_subtree(self):
        """Deleting a node with children removes the entire subtree."""
        builder = SubtreeBuilder()
        inner = builder.source.group()
        inner.leaf("Child1")
        inner.leaf("Child2")
        builder.build()
        builder.subscribe()

        assert "Child1" in builder.render()
        assert "Child2" in builder.render()

        builder.source.del_item("group_0")

        assert "Child1" not in builder.render()
        assert "Child2" not in builder.render()


# =============================================================================
# Tests: Source insert (requires subscribe for reactivity)
# =============================================================================


class TestAutonomousSourceInsert:
    """Tests for reactive source insertion."""

    def test_source_insert_updates_output(self):
        """Inserting a node into the source adds it to output."""
        builder = TestBuilder()
        builder.source.heading("Title")
        builder.build()
        builder.subscribe()

        assert "[heading:Title]" in builder.render()
        assert "Extra" not in builder.render()

        builder.source.text("Extra")

        assert "Extra" in builder.render()
        assert "[heading:Title]" in builder.render()

    def test_source_insert_with_pointer(self):
        """Inserted node with ^pointer gets bound to data."""
        builder = TestBuilder()
        builder.data["dynamic"] = "Resolved"
        builder.source.heading("Static")
        builder.build()
        builder.subscribe()

        assert "Resolved" not in builder.render()

        builder.source.text("^dynamic")

        assert "Resolved" in builder.render()

    def test_source_insert_at_position(self):
        """Inserted node appears at the correct position."""
        builder = TestBuilder()
        builder.source.heading("First")
        builder.source.heading("Third")
        builder.build()
        builder.subscribe()

        builder.source.text("Second", node_position=1)

        assert builder.render() is not None
        first_pos = builder.render().index("First")
        second_pos = builder.render().index("Second")
        third_pos = builder.render().index("Third")
        assert first_pos < second_pos < third_pos


# =============================================================================
# Tests: Source update (requires subscribe for reactivity)
# =============================================================================


class TestAutonomousSourceUpdate:
    """Tests for reactive source value/attribute updates."""

    def test_source_update_value(self):
        """Updating a node value in the source updates the output."""
        builder = TestBuilder()
        builder.source.heading("Original")
        builder.build()
        builder.subscribe()

        assert "Original" in builder.render()

        builder.source.set_item("heading_0", "Modified")

        assert "Modified" in builder.render()
        assert "Original" not in builder.render()

    def test_source_update_attr(self):
        """Updating a node attribute in the source updates the output."""
        builder = TestBuilder()
        builder.source.item(color="red")
        builder.build()
        builder.subscribe()

        assert "color=red" in builder.render()

        builder.source.set_attr("item_0", color="blue")

        assert "color=blue" in builder.render()
        assert "color=red" not in builder.render()

    def test_source_update_pointer_rebind(self):
        """Updating a static value to a ^pointer binds it to data."""
        builder = TestBuilder()
        builder.data["title"] = "Dynamic"
        builder.source.heading("static")
        builder.build()
        builder.subscribe()

        assert "static" in builder.render()
        assert "Dynamic" not in builder.render()

        builder.source.set_item("heading_0", "^title")

        assert "Dynamic" in builder.render()

    def test_source_update_value_replaces_subtree(self):
        """Updating a node that had children replaces the entire subtree."""
        builder = SubtreeBuilder()
        builder.data["child_a"] = "A"
        builder.data["child_b"] = "B"
        inner = builder.source.group()
        inner.leaf("^child_a")
        inner.leaf("^child_b")
        builder.build()
        builder.subscribe()

        assert "A" in builder.render()
        assert "B" in builder.render()

        builder.source.set_item("group_0", "replaced")

        assert "replaced" in builder.render()
        assert "A" not in builder.render()
        assert "B" not in builder.render()


# =============================================================================
# Tests: Compiled observability (requires subscribe)
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
        builder.subscribe()

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
        builder.subscribe()

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
        builder.subscribe()

        builder.built.subscribe(
            "test", update=lambda **kw: events.append(("upd", kw.get("reason"))),
        )

        builder.source.set_item("heading_0", "Modified")

        assert len(events) >= 1
        assert any(e[1] == "source" for e in events)


# =============================================================================
# Tests: Map adequacy (requires subscribe for reactivity)
# =============================================================================


class TestAutonomousReactiveAfterInsert:
    """Tests that reactivity works after incremental insert."""

    def test_insert_reactive_after_subscribe(self):
        """After insert, data changes propagate to the new node."""
        builder = TestBuilder()
        builder.data["val"] = "first"
        builder.source.heading("static")
        builder.build()
        builder.subscribe()

        builder.source.text("^val")
        assert "first" in builder.render()

        builder.data["val"] = "second"
        assert "second" in builder.render()
