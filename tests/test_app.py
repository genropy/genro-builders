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

    def compile_bound(self, bound_bag):
        return self._render(bound_bag)

    def _render(self, bag):
        parts = []
        for node in bag:
            tag = node.tag or node.label
            value = node.static_value
            if isinstance(value, Bag):
                children = self._render(value)
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


TestBuilder.compiler_class = TestCompiler


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

            def recipe(self, store):
                nonlocal recipe_called
                recipe_called = True
                store.heading("Hello")

        app = MyApp()
        app.setup()

        assert recipe_called
        assert app.output is not None
        assert "[heading:Hello]" in app.output

    def test_compile_returns_output(self):
        """compile() returns the rendered output."""

        class MyApp(BagAppBase):
            builder_class = TestBuilder

            def recipe(self, store):
                store.text("content")

        app = MyApp()
        app.recipe(app.store)
        result = app.compile()

        assert result == app.output
        assert "[text:content]" in result


class TestAppPointerResolution:
    """Tests for ^pointer resolution in app mode."""

    def test_pointer_in_value(self):
        """^pointer in node value is resolved from data."""

        class MyApp(BagAppBase):
            builder_class = TestBuilder

            def recipe(self, store):
                store.heading("^page.title")

        app = MyApp()
        app.data["page.title"] = "Hello World"
        app.setup()

        assert "Hello World" in app.output

    def test_pointer_in_attr(self):
        """^pointer in node attribute is resolved from data."""

        class MyApp(BagAppBase):
            builder_class = TestBuilder

            def recipe(self, store):
                store.item(color="^theme.color")

        app = MyApp()
        app.data["theme.color"] = "blue"
        app.setup()

        assert "color=blue" in app.output

    def test_multiple_pointers(self):
        """Multiple pointers in same recipe."""

        class MyApp(BagAppBase):
            builder_class = TestBuilder

            def recipe(self, store):
                store.heading("^title")
                store.text("^body")

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

            def recipe(self, store):
                store.heading("^title")

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

            def recipe(self, store):
                store.heading("^title")
                store.text("static content")

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

            def recipe(self, store):
                nonlocal call_count
                call_count += 1
                store.heading("^title")

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

            def recipe(self, store):
                store.heading("^name")

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

            def recipe(self, store):
                store.section(title="^section.title")

        app = MyApp()
        app.data["section.title"] = "My Section"
        app.setup()

        assert "My Section" in app.output
        assert "default content" in app.output


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
        app.recipe(app.store)

        with pytest.raises(RuntimeError, match="no compiler"):
            app.compile()
