# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for BuilderManager hooks: store, main, reactive_store."""
from __future__ import annotations

from genro_bag import Bag

from genro_builders.manager import BuilderManager

from .helpers import TestBuilder


class TestStore:
    """Tests for store hook."""

    def test_store_populates_store(self):
        """store() sets shared values at store root."""

        class App(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", TestBuilder)

            def store(self, store):
                store["title"] = "Hello"

            def main(self, source):
                source.heading("^title")

        app = App()
        app.build()
        assert "Hello" in app.page.output

    def test_store_accessible_by_all_builders(self):
        """Shared data is accessible by all builders."""

        class App(BuilderManager):
            def __init__(self):
                self.a = self.set_builder("a", TestBuilder)
                self.b = self.set_builder("b", TestBuilder)

            def store(self, store):
                store["shared"] = "Common Value"

            def main_a(self, source):
                source.heading("^shared")

            def main_b(self, source):
                source.text("^shared")

        app = App()
        app.build()
        assert "Common Value" in app.a.output
        assert "Common Value" in app.b.output


class TestMainHook:
    """Tests for main dispatch."""

    def test_single_builder_uses_main(self):
        """Single builder calls main(source)."""

        class App(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", TestBuilder)

            def main(self, source):
                source.heading("From Main")

        app = App()
        app.build()
        assert "From Main" in app.page.output

    def test_multi_builder_uses_main_name(self):
        """Multiple builders call main_<name>(source)."""

        class App(BuilderManager):
            def __init__(self):
                self.content = self.set_builder("content", TestBuilder)
                self.sidebar = self.set_builder("sidebar", TestBuilder)

            def main_content(self, source):
                source.heading("Main Content")

            def main_sidebar(self, source):
                source.text("Sidebar")

        app = App()
        app.build()
        assert "Main Content" in app.content.output
        assert "Sidebar" in app.sidebar.output

    def test_main_name_takes_precedence(self):
        """main_<name> takes precedence over main."""

        class App(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", TestBuilder)

            def main(self, source):
                source.heading("Generic")

            def main_page(self, source):
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

    def test_store_sets_private_data(self):
        """Private data can be set via store()."""

        class App(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", TestBuilder)

            def store(self, store):
                store["builders.page.color"] = "blue"

            def main(self, source):
                source.heading("test")

        app = App()
        app.build()
        assert app.reactive_store["builders.page.color"] == "blue"

    def test_store_root_is_reactive_store(self):
        """Store argument is the reactive store root."""

        class App(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", TestBuilder)

            def store(self, store):
                store["title"] = "Hello"

            def main(self, source):
                source.heading("^title")

        app = App()
        app.build()
        assert "Hello" in app.page.output

    def test_multi_builder_private_data_isolated(self):
        """Each builder's private data is isolated."""

        class App(BuilderManager):
            def __init__(self):
                self.a = self.set_builder("a", TestBuilder)
                self.b = self.set_builder("b", TestBuilder)

            def store(self, store):
                store["builders.a.value"] = "A-private"
                store["builders.b.value"] = "B-private"

            def main_a(self, source):
                source.heading("test")

            def main_b(self, source):
                source.heading("test")

        app = App()
        app.build()
        assert app.reactive_store["builders.a.value"] == "A-private"
        assert app.reactive_store["builders.b.value"] == "B-private"


class TestBuildPipeline:
    """Tests for full build pipeline."""

    def test_pipeline_order(self):
        """store → main → build in correct order."""
        order = []

        class App(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", TestBuilder)

            def store(self, store):
                order.append("store")
                store["title"] = "Hello"

            def main(self, source):
                order.append("main")
                source.heading("^title")

        app = App()
        app.build()
        assert order == ["store", "main"]
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
