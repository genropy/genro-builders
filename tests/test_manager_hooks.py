# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for BuilderManager hooks: common_data, recipe, reactive_store."""
from __future__ import annotations

from genro_bag import Bag

from genro_builders.manager import BuilderManager

from .helpers import TestBuilder


class TestCommonData:
    """Tests for common_data hook."""

    def test_common_data_populates_store(self):
        """common_data sets shared values at store root."""

        class App(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", TestBuilder)

            def common_data(self, store):
                store["title"] = "Hello"

            def recipe(self, source, common, data):
                source.heading("^title")

        app = App()
        app.build()
        assert "Hello" in app.page.output

    def test_common_data_accessible_by_all_builders(self):
        """Shared data is accessible by all builders."""

        class App(BuilderManager):
            def __init__(self):
                self.a = self.set_builder("a", TestBuilder)
                self.b = self.set_builder("b", TestBuilder)

            def common_data(self, store):
                store["shared"] = "Common Value"

            def recipe_a(self, source, common, data):
                source.heading("^shared")

            def recipe_b(self, source, common, data):
                source.text("^shared")

        app = App()
        app.build()
        assert "Common Value" in app.a.output
        assert "Common Value" in app.b.output


class TestRecipeHook:
    """Tests for recipe dispatch."""

    def test_single_builder_uses_recipe(self):
        """Single builder calls recipe(source, common, data)."""

        class App(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", TestBuilder)

            def recipe(self, source, common, data):
                source.heading("From Recipe")

        app = App()
        app.build()
        assert "From Recipe" in app.page.output

    def test_multi_builder_uses_recipe_name(self):
        """Multiple builders call recipe_<name>(source, common, data)."""

        class App(BuilderManager):
            def __init__(self):
                self.main = self.set_builder("main", TestBuilder)
                self.sidebar = self.set_builder("sidebar", TestBuilder)

            def recipe_main(self, source, common, data):
                source.heading("Main Content")

            def recipe_sidebar(self, source, common, data):
                source.text("Sidebar")

        app = App()
        app.build()
        assert "Main Content" in app.main.output
        assert "Sidebar" in app.sidebar.output

    def test_recipe_name_takes_precedence(self):
        """recipe_<name> takes precedence over recipe."""

        class App(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", TestBuilder)

            def recipe(self, source, common, data):
                source.heading("Generic")

            def recipe_page(self, source, common, data):
                source.heading("Specific")

        app = App()
        app.build()
        assert "Specific" in app.page.output


class TestPrivateData:
    """Tests for per-builder private data namespace."""

    def test_private_namespace_created(self):
        """set_builder creates builders.<name> in the store."""

        class App(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", TestBuilder)

        app = App()
        builders = app.reactive_store.get_item("builders")
        assert builders is not None
        assert isinstance(builders, Bag)
        page_data = builders.get_item("page")
        assert page_data is not None
        assert isinstance(page_data, Bag)

    def test_recipe_receives_private_data(self):
        """Recipe data argument is the builder's private namespace."""

        class App(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", TestBuilder)

            def recipe(self, source, common, data):
                data["color"] = "blue"
                source.heading("test")

        app = App()
        app.build()
        assert app.reactive_store["builders.page.color"] == "blue"

    def test_recipe_common_is_store_root(self):
        """Recipe common argument is the reactive store root."""

        class App(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", TestBuilder)

            def common_data(self, store):
                store["title"] = "Hello"

            def recipe(self, source, common, data):
                assert common["title"] == "Hello"
                source.heading("^title")

        app = App()
        app.build()

    def test_multi_builder_private_data_isolated(self):
        """Each builder's private data is isolated."""

        class App(BuilderManager):
            def __init__(self):
                self.a = self.set_builder("a", TestBuilder)
                self.b = self.set_builder("b", TestBuilder)

            def recipe_a(self, source, common, data):
                data["value"] = "A-private"
                source.heading("test")

            def recipe_b(self, source, common, data):
                data["value"] = "B-private"
                source.heading("test")

        app = App()
        app.build()
        assert app.reactive_store["builders.a.value"] == "A-private"
        assert app.reactive_store["builders.b.value"] == "B-private"


class TestBuildPipeline:
    """Tests for full build pipeline."""

    def test_pipeline_order(self):
        """common_data → recipe → build in correct order."""
        order = []

        class App(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", TestBuilder)

            def common_data(self, store):
                order.append("common_data")
                store["title"] = "Hello"

            def recipe(self, source, common, data):
                order.append("recipe")
                source.heading("^title")

        app = App()
        app.build()
        assert order == ["common_data", "recipe"]
        assert "Hello" in app.page.output

    def test_reactive_store_property(self):
        """reactive_store property returns the data Bag."""

        class App(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", TestBuilder)

        app = App()
        assert isinstance(app.reactive_store, Bag)
        assert app.reactive_store.backref is True

    def test_no_hooks_manual_usage(self):
        """Manager without hooks — user populates manually."""

        class App(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", TestBuilder)

        app = App()
        app.page.source.heading("Manual")
        app.build_all()
        assert "Manual" in app.page.output
