# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for BuilderManager hooks: reactive_store and recipe."""
from __future__ import annotations

from genro_builders.manager import BuilderManager

from .helpers import TestBuilder


class TestReactiveStore:
    """Tests for reactive_store hook."""

    def test_reactive_store_populates_data(self):
        """reactive_store is called during build and populates data."""

        class App(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", TestBuilder)

            def reactive_store(self, data):
                data["title"] = "Hello"

            def recipe(self, source):
                source.heading("^title")

        app = App()
        app.build()
        assert "Hello" in app.page.output

    def test_data_override_after_reactive_store(self):
        """Data set after init overrides reactive_store defaults on rebuild."""

        class App(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", TestBuilder)

            def reactive_store(self, data):
                data["title"] = "Default"

            def recipe(self, source):
                source.heading("^title")

        app = App()
        app.build()
        assert "Default" in app.page.output

        app.data["title"] = "Custom"
        assert "Custom" in app.page.output

    def test_no_reactive_store(self):
        """Manager without reactive_store works fine."""

        class App(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", TestBuilder)

            def recipe(self, source):
                source.heading("Static")

        app = App()
        app.build()
        assert "Static" in app.page.output


class TestRecipeHook:
    """Tests for recipe hook dispatch."""

    def test_single_builder_uses_recipe(self):
        """Single builder calls recipe(source)."""

        class App(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", TestBuilder)

            def recipe(self, source):
                source.heading("From Recipe")

        app = App()
        app.build()
        assert "From Recipe" in app.page.output

    def test_multi_builder_uses_recipe_name(self):
        """Multiple builders call recipe_<name>(source)."""

        class App(BuilderManager):
            def __init__(self):
                self.main = self.set_builder("main", TestBuilder)
                self.sidebar = self.set_builder("sidebar", TestBuilder)

            def recipe_main(self, source):
                source.heading("Main Content")

            def recipe_sidebar(self, source):
                source.text("Sidebar")

        app = App()
        app.build()
        assert "Main Content" in app.main.output
        assert "Sidebar" in app.sidebar.output

    def test_recipe_name_takes_precedence(self):
        """recipe_<name> takes precedence over recipe for named builder."""

        class App(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", TestBuilder)

            def recipe(self, source):
                source.heading("Generic")

            def recipe_page(self, source):
                source.heading("Specific")

        app = App()
        app.build()
        assert "Specific" in app.page.output

    def test_no_recipe(self):
        """Manager without recipe — user populates source manually."""

        class App(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", TestBuilder)

        app = App()
        app.page.source.heading("Manual")
        app.build_all()
        assert "Manual" in app.page.output


class TestBuildPipeline:
    """Tests for full build pipeline: reactive_store → recipe → build_all."""

    def test_full_pipeline(self):
        """reactive_store → recipe → build in correct order."""
        order = []

        class App(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", TestBuilder)

            def reactive_store(self, data):
                order.append("store")
                data["title"] = "Hello"

            def recipe(self, source):
                order.append("recipe")
                source.heading("^title")

        app = App()
        app.build()
        assert order == ["store", "recipe"]
        assert "Hello" in app.page.output

    def test_full_pipeline_multi_builder(self):
        """Full pipeline with multiple builders and shared data."""

        class App(BuilderManager):
            def __init__(self):
                self.a = self.set_builder("a", TestBuilder)
                self.b = self.set_builder("b", TestBuilder)

            def reactive_store(self, data):
                data["shared"] = "Shared Value"

            def recipe_a(self, source):
                source.heading("^shared")

            def recipe_b(self, source):
                source.text("^shared")

        app = App()
        app.build()
        assert "Shared Value" in app.a.output
        assert "Shared Value" in app.b.output
