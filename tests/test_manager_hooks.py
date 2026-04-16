# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for BuilderManager hooks: main, setup, build."""
from __future__ import annotations

from genro_bag import Bag

from genro_builders.manager import BuilderManager

from .helpers import TestBuilder


class TestDataPopulation:
    """Tests for populating data via global_store / local_store."""

    def test_local_store_populates_data(self):
        """local_store sets values in the builder's namespace."""

        class App(BuilderManager):
            def on_init(self):
                self.page = self.register_builder("page", TestBuilder)

            def main(self, source):
                self.local_store()["title"] = "Hello"
                source.heading("^title")

        app = App()
        app.setup()
        app.build()
        assert "Hello" in app.page.render()

    def test_cross_builder_data_via_volume(self):
        """Data from one builder accessible by another via volume syntax."""

        class App(BuilderManager):
            def on_init(self):
                self.a = self.register_builder("a", TestBuilder)
                self.b = self.register_builder("b", TestBuilder)

            def main_a(self, source):
                self.local_store()["shared"] = "Common Value"
                source.heading("^shared")

            def main_b(self, source):
                source.text("^a:shared")

        app = App()
        app.setup()
        app.build()
        assert "Common Value" in app.a.render()
        assert "Common Value" in app.b.render()


class TestMainHook:
    """Tests for main dispatch."""

    def test_single_builder_uses_main(self):
        """Single builder calls main(source)."""

        class App(BuilderManager):
            def on_init(self):
                self.page = self.register_builder("page", TestBuilder)

            def main(self, source):
                source.heading("From Main")

        app = App()
        app.setup()
        app.build()
        assert "From Main" in app.page.render()

    def test_multi_builder_uses_main_name(self):
        """Multiple builders call main_<name>(source)."""

        class App(BuilderManager):
            def on_init(self):
                self.content = self.register_builder("content", TestBuilder)
                self.sidebar = self.register_builder("sidebar", TestBuilder)

            def main_content(self, source):
                source.heading("Main Content")

            def main_sidebar(self, source):
                source.text("Sidebar")

        app = App()
        app.setup()
        app.build()
        assert "Main Content" in app.content.render()
        assert "Sidebar" in app.sidebar.render()

    def test_main_name_takes_precedence(self):
        """main_<name> takes precedence over main."""

        class App(BuilderManager):
            def on_init(self):
                self.page = self.register_builder("page", TestBuilder)

            def main(self, source):
                source.heading("Generic")

            def main_page(self, source):
                source.heading("Specific")

        app = App()
        app.setup()
        app.build()
        assert "Specific" in app.page.render()


class TestPrivateData:
    """Tests for per-builder private data namespace."""

    def test_private_namespace_created(self):
        """register_builder creates <name> namespace directly in the store."""

        class App(BuilderManager):
            def on_init(self):
                self.page = self.register_builder("page", TestBuilder)

        app = App()
        page_data = app.global_store.get_item("page")
        assert page_data is not None
        assert isinstance(page_data, Bag)

    def test_private_data_set_via_global_store(self):
        """Private data can be set via global_store path."""

        class App(BuilderManager):
            def on_init(self):
                self.page = self.register_builder("page", TestBuilder)

            def main(self, source):
                self.global_store["page.color"] = "blue"
                source.heading("test")

        app = App()
        app.setup()
        app.build()
        assert app.global_store["page.color"] == "blue"

    def test_private_data_set_via_local_store(self):
        """Private data can be set via local_store."""

        class App(BuilderManager):
            def on_init(self):
                self.page = self.register_builder("page", TestBuilder)

            def main(self, source):
                self.local_store()["color"] = "red"
                source.heading("test")

        app = App()
        app.setup()
        app.build()
        assert app.global_store["page.color"] == "red"

    def test_multi_builder_private_data_isolated(self):
        """Each builder's private data is isolated."""

        class App(BuilderManager):
            def on_init(self):
                self.a = self.register_builder("a", TestBuilder)
                self.b = self.register_builder("b", TestBuilder)

            def main_a(self, source):
                self.local_store()["value"] = "A-private"
                source.heading("test")

            def main_b(self, source):
                self.local_store()["value"] = "B-private"
                source.heading("test")

        app = App()
        app.setup()
        app.build()
        assert app.global_store["a.value"] == "A-private"
        assert app.global_store["b.value"] == "B-private"


class TestBuildPipeline:
    """Tests for full build pipeline."""

    def test_setup_then_build(self):
        """setup → build produces output."""

        class App(BuilderManager):
            def on_init(self):
                self.page = self.register_builder("page", TestBuilder)

            def main(self, source):
                self.local_store()["title"] = "Hello"
                source.heading("^title")

        app = App()
        app.setup()
        app.build()
        assert "Hello" in app.page.render()

    def test_global_store_property(self):
        """global_store property returns the data Bag."""

        class App(BuilderManager):
            def on_init(self):
                self.page = self.register_builder("page", TestBuilder)

        app = App()
        assert isinstance(app.global_store, Bag)
        assert app.global_store.backref is True

    def test_no_hooks_manual_usage(self):
        """Manager without hooks — user populates source manually."""

        class App(BuilderManager):
            def on_init(self):
                self.page = self.register_builder("page", TestBuilder)

        app = App()
        app.page.source.heading("Manual")
        app.build()
        assert "Manual" in app.page.render()
