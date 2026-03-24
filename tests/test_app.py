# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for BagAppBase — reactive application runtime."""
from __future__ import annotations

from genro_bag import Bag
from genro_builders import BagBuilderBase, BagCompilerBase
from genro_builders.app import BagAppBase
from genro_builders.builder_bag import BuilderBag
from genro_builders.builders import component, element
from genro_builders.compiler import compile_handler


# =============================================================================
# Test builder and compiler
# =============================================================================


class TestBuilder(BagBuilderBase):
    """Simple builder for testing."""

    @element()
    def heading(self): ...

    @element()
    def text(self): ...

    @element()
    def item(self): ...

    @component()
    def section(self, comp, title=None, **kwargs):
        comp.heading(title)
        comp.text("default content")


class TestCompiler(BagCompilerBase):
    """Simple compiler that renders tags with values."""

    def render(self, compiled_bag):
        return self._render_bag(compiled_bag)

    def _render_bag(self, bag):
        parts = []
        for node in bag:
            tag = node.node_tag or node.label
            value = node.static_value
            if isinstance(value, Bag):
                children = self._render_bag(value)
                parts.append(f"[{tag}:{children}]")
            elif value is not None:
                parts.append(f"[{tag}:{value}]")
            else:
                attrs = {k: v for k, v in node.attr.items() if not k.startswith("_")}
                if attrs:
                    attr_str = ",".join(f"{k}={v}" for k, v in attrs.items())
                    parts.append(f"[{tag}:{attr_str}]")
                else:
                    parts.append(f"[{tag}]")
        return "".join(parts)


TestBuilder._compiler_class = TestCompiler


# =============================================================================
# Tests
# =============================================================================


class TestAppLifecycle:
    """Tests for basic app lifecycle."""

    def test_setup_calls_recipe_and_compile(self):
        """setup() calls recipe() and compiles."""
        recipe_called = False

        class MyApp(BagAppBase):
            builder_class = TestBuilder

            def recipe(self, source):
                nonlocal recipe_called
                recipe_called = True
                source.heading("Hello")

        app = MyApp()
        app.setup()

        assert recipe_called
        assert app.output is not None
        assert "[heading:Hello]" in app.output

    def test_compile_returns_output(self):
        """compile() returns the rendered output."""

        class MyApp(BagAppBase):
            builder_class = TestBuilder

            def recipe(self, source):
                source.text("content")

        app = MyApp()
        app.recipe(app.source)
        result = app.compile()

        assert result == app.output
        assert "[text:content]" in result


class TestAppPointerResolution:
    """Tests for ^pointer resolution in app mode."""

    def test_pointer_in_value(self):
        """^pointer in node value is resolved from data."""

        class MyApp(BagAppBase):
            builder_class = TestBuilder

            def recipe(self, source):
                source.heading("^page.title")

        app = MyApp()
        app.data["page.title"] = "Hello World"
        app.setup()

        assert "Hello World" in app.output

    def test_pointer_in_attr(self):
        """^pointer in node attribute is resolved from data."""

        class MyApp(BagAppBase):
            builder_class = TestBuilder

            def recipe(self, source):
                source.item(color="^theme.color")

        app = MyApp()
        app.data["theme.color"] = "blue"
        app.setup()

        assert "color=blue" in app.output

    def test_multiple_pointers(self):
        """Multiple pointers in same recipe."""

        class MyApp(BagAppBase):
            builder_class = TestBuilder

            def recipe(self, source):
                source.heading("^title")
                source.text("^body")

        app = MyApp()
        app.data["title"] = "Title"
        app.data["body"] = "Body text"
        app.setup()

        assert "Title" in app.output
        assert "Body text" in app.output


class TestAppReactivity:
    """Tests for reactive data updates."""

    def test_data_change_updates_output(self):
        """Changing data after setup updates the output."""

        class MyApp(BagAppBase):
            builder_class = TestBuilder

            def recipe(self, source):
                source.heading("^title")

        app = MyApp()
        app.data["title"] = "Original"
        app.setup()

        assert "Original" in app.output

        app.data["title"] = "Updated"

        assert "Updated" in app.output

    def test_data_change_partial_update(self):
        """Only nodes bound to changed data are updated."""

        class MyApp(BagAppBase):
            builder_class = TestBuilder

            def recipe(self, source):
                source.heading("^title")
                source.text("static content")

        app = MyApp()
        app.data["title"] = "Hello"
        app.setup()

        assert "Hello" in app.output
        assert "static content" in app.output

        app.data["title"] = "Changed"

        assert "Changed" in app.output
        assert "static content" in app.output


class TestAppRebuild:
    """Tests for full rebuild on recipe change."""

    def test_rebuild_reruns_recipe(self):
        """rebuild() clears and re-runs recipe."""
        call_count = 0

        class MyApp(BagAppBase):
            builder_class = TestBuilder

            def recipe(self, source):
                nonlocal call_count
                call_count += 1
                source.heading("^title")

        app = MyApp()
        app.data["title"] = "v1"
        app.setup()

        assert call_count == 1

        app.data["title"] = "v2"
        app.rebuild()

        assert call_count == 2
        assert "v2" in app.output


class TestAppDataReplacement:
    """Tests for replacing the entire data Bag."""

    def test_replace_data_rebinds(self):
        """Setting data property replaces and rebinds."""

        class MyApp(BagAppBase):
            builder_class = TestBuilder

            def recipe(self, source):
                source.heading("^name")

        app = MyApp()
        app.data["name"] = "Alice"
        app.setup()

        assert "Alice" in app.output

        # Replace entire data
        new_data = Bag()
        new_data["name"] = "Bob"
        app.data = new_data

        assert "Bob" in app.output


class TestAppWithComponent:
    """Tests for app with component expansion."""

    def test_component_expanded_and_bound(self):
        """Components are expanded and their pointers are resolved."""

        class MyApp(BagAppBase):
            builder_class = TestBuilder

            def recipe(self, source):
                source.section(title="^section.title")

        app = MyApp()
        app.data["section.title"] = "My Section"
        app.setup()

        assert "My Section" in app.output
        assert "default content" in app.output


class TestAppSourceDelete:
    """Tests for reactive source deletion."""

    def test_source_delete_updates_output(self):
        """Deleting a node from the source removes it from output."""

        class MyApp(BagAppBase):
            builder_class = TestBuilder

            def recipe(self, source):
                source.heading("Title")
                source.text("Content")

        app = MyApp()
        app.setup()

        assert "[heading:Title]" in app.output
        assert "[text:Content]" in app.output

        app.source.del_item("text_0")
        assert "[text:Content]" not in app.output
        assert "[heading:Title]" in app.output

    def test_source_delete_with_pointer_cleanup(self):
        """Deleting a node with ^pointer cleans up the subscription map."""

        class MyApp(BagAppBase):
            builder_class = TestBuilder

            def recipe(self, source):
                source.heading("^title")
                source.text("static")

        app = MyApp()
        app.data["title"] = "Hello"
        app.setup()

        assert "Hello" in app.output

        # The heading node is bound to 'title' in the subscription map
        assert len(app._binding.subscription_map) > 0

        app.source.del_item("heading_0")

        # After delete, the binding for the deleted node should be gone
        for entries in app._binding.subscription_map.values():
            for target_node, _location in entries:
                assert target_node.compiled.get("path") != "heading_0"

        assert "Hello" not in app.output
        assert "[text:static]" in app.output

    def test_source_delete_subtree(self):
        """Deleting a node with children removes the entire subtree from output."""

        class SubtreeBuilder(BagBuilderBase):
            @element(sub_tags="*")
            def group(self): ...

            @element()
            def leaf(self): ...

        SubtreeBuilder._compiler_class = TestCompiler

        class MyApp(BagAppBase):
            builder_class = SubtreeBuilder

            def recipe(self, source):
                inner = source.group()
                inner.leaf("Child1")
                inner.leaf("Child2")

        app = MyApp()
        app.setup()

        assert "Child1" in app.output
        assert "Child2" in app.output

        app.source.del_item("group_0")

        assert "Child1" not in app.output
        assert "Child2" not in app.output


class TestAppSourceInsert:
    """Tests for reactive source insertion."""

    def test_source_insert_updates_output(self):
        """Inserting a node into the source adds it to output."""

        class MyApp(BagAppBase):
            builder_class = TestBuilder

            def recipe(self, source):
                source.heading("Title")

        app = MyApp()
        app.setup()

        assert "[heading:Title]" in app.output
        assert "Extra" not in app.output

        app.source.text("Extra")

        assert "Extra" in app.output
        assert "[heading:Title]" in app.output

    def test_source_insert_with_pointer(self):
        """Inserted node with ^pointer gets bound to data."""

        class MyApp(BagAppBase):
            builder_class = TestBuilder

            def recipe(self, source):
                source.heading("Static")

        app = MyApp()
        app.data["dynamic"] = "Resolved"
        app.setup()

        assert "Resolved" not in app.output

        app.source.text("^dynamic")

        assert "Resolved" in app.output

    def test_source_insert_at_position(self):
        """Inserted node appears at the correct position."""

        class MyApp(BagAppBase):
            builder_class = TestBuilder

            def recipe(self, source):
                source.heading("First")
                source.heading("Third")

        app = MyApp()
        app.setup()

        # Insert between First and Third
        app.source.text("Second", node_position=1)

        assert app.output is not None
        first_pos = app.output.index("First")
        second_pos = app.output.index("Second")
        third_pos = app.output.index("Third")
        assert first_pos < second_pos < third_pos


class TestAppSourceUpdate:
    """Tests for reactive source value/attribute updates."""

    def test_source_update_value(self):
        """Updating a node value in the source updates the output."""

        class MyApp(BagAppBase):
            builder_class = TestBuilder

            def recipe(self, source):
                source.heading("Original")

        app = MyApp()
        app.setup()

        assert "Original" in app.output

        # Update the node value via set_item (overwrites)
        app.source.set_item("heading_0", "Modified")

        assert "Modified" in app.output
        assert "Original" not in app.output

    def test_source_update_attr(self):
        """Updating a node attribute in the source updates the output."""

        class MyApp(BagAppBase):
            builder_class = TestBuilder

            def recipe(self, source):
                source.item(color="red")

        app = MyApp()
        app.setup()

        assert "color=red" in app.output

        app.source.set_attr("item_0", color="blue")

        assert "color=blue" in app.output
        assert "color=red" not in app.output

    def test_source_update_pointer_rebind(self):
        """Updating a static value to a ^pointer binds it to data."""

        class MyApp(BagAppBase):
            builder_class = TestBuilder

            def recipe(self, source):
                source.heading("static")

        app = MyApp()
        app.data["title"] = "Dynamic"
        app.setup()

        assert "static" in app.output
        assert "Dynamic" not in app.output

        # Replace static value with a pointer
        app.source.set_item("heading_0", "^title")

        assert "Dynamic" in app.output

    def test_source_update_value_replaces_subtree(self):
        """Updating a node that had children replaces the entire subtree."""

        class SubtreeBuilder(BagBuilderBase):
            @element(sub_tags="*")
            def group(self): ...

            @element()
            def leaf(self): ...

        SubtreeBuilder._compiler_class = TestCompiler

        class MyApp(BagAppBase):
            builder_class = SubtreeBuilder

            def recipe(self, source):
                inner = source.group()
                inner.leaf("^child_a")
                inner.leaf("^child_b")

        app = MyApp()
        app.data["child_a"] = "A"
        app.data["child_b"] = "B"
        app.setup()

        assert "A" in app.output
        assert "B" in app.output

        # Count bindings before
        bindings_before = sum(len(v) for v in app._binding.subscription_map.values())

        # Replace the group node value with a scalar — children disappear
        app.source.set_item("group_0", "replaced")

        assert "replaced" in app.output
        assert "A" not in app.output
        assert "B" not in app.output

        # Old bindings for child_a and child_b should be gone
        bindings_after = sum(len(v) for v in app._binding.subscription_map.values())
        assert bindings_after < bindings_before


class TestAppCompiledObservable:
    """Tests for compiled bag observability (live app support)."""

    def test_compiled_bag_notifies_on_source_delete(self):
        """Subscriber on compiled bag receives delete events from source changes."""
        events = []

        class MyApp(BagAppBase):
            builder_class = TestBuilder

            def recipe(self, source):
                source.heading("Title")
                source.text("Content")

        app = MyApp()
        app.setup()

        app.compiled.subscribe("test", delete=lambda **kw: events.append(("del", kw.get("reason"))))

        app.source.del_item("text_0")

        assert len(events) == 1
        assert events[0] == ("del", "source")

    def test_compiled_bag_notifies_on_source_insert(self):
        """Subscriber on compiled bag receives insert events from source changes."""
        events = []

        class MyApp(BagAppBase):
            builder_class = TestBuilder

            def recipe(self, source):
                source.heading("Title")

        app = MyApp()
        app.setup()

        app.compiled.subscribe("test", insert=lambda **kw: events.append(("ins", kw.get("reason"))))

        app.source.text("Extra")

        assert len(events) == 1
        assert events[0] == ("ins", "source")

    def test_compiled_bag_notifies_on_source_update_value(self):
        """Subscriber on compiled bag receives update events from source value changes."""
        events = []

        class MyApp(BagAppBase):
            builder_class = TestBuilder

            def recipe(self, source):
                source.heading("Original")

        app = MyApp()
        app.setup()

        app.compiled.subscribe("test", update=lambda **kw: events.append(("upd", kw.get("reason"))))

        app.source.set_item("heading_0", "Modified")

        assert len(events) >= 1
        assert any(e[1] == "source" for e in events)


class TestAppNoCompiler:
    """Tests for error handling."""

    def test_no_compiler_raises(self):
        """App without compiler raises RuntimeError on compile."""
        import pytest

        class NoCompBuilder(BagBuilderBase):
            @element()
            def div(self): ...

        class MyApp(BagAppBase):
            builder_class = NoCompBuilder

        app = MyApp()
        app.recipe(app.source)

        with pytest.raises(RuntimeError, match="no compiler"):
            app.compile()
