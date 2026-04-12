# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for BuilderManager — multi-builder coordination with shared data."""
from __future__ import annotations

from genro_bag import Bag

from genro_builders.manager import BuilderManager

from .helpers import TestBuilder


class TestManagerBasics:
    """Tests for basic BuilderManager operations."""

    def test_set_builder(self):
        """set_builder creates and returns a builder."""

        class App(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", TestBuilder)

        app = App()
        assert app.page is not None
        assert app.page._manager is app

    def test_builder_data_proxied_to_manager(self):
        """Builder.data returns the manager's shared data."""

        class App(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", TestBuilder)

        app = App()
        assert app.page.data is app.reactive_store

    def test_manager_data_is_backref_enabled(self):
        """Manager's data Bag has backref enabled by __init_subclass__."""

        class App(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", TestBuilder)

        app = App()
        assert app.reactive_store.backref is True

    def test_no_super_init_needed(self):
        """Subclass __init__ does not need super().__init__()."""

        class App(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", TestBuilder)
                self.custom = "value"

        app = App()
        assert app.custom == "value"
        assert app.page is not None
        assert isinstance(app.reactive_store, Bag)


class TestManagerMultipleBuilders:
    """Tests for multiple builders sharing data."""

    def test_multiple_builders_share_data(self):
        """Two registered builders share the same data."""

        class App(BuilderManager):
            def __init__(self):
                self.b1 = self.set_builder("page", TestBuilder)
                self.b2 = self.set_builder("sidebar", TestBuilder)

        app = App()
        assert app.b1.data is app.b2.data
        assert app.b1.data is app.reactive_store

    def test_data_replacement_propagates(self):
        """Replacing manager.data updates all builders."""

        class App(BuilderManager):
            def __init__(self):
                self.b1 = self.set_builder("page", TestBuilder)
                self.b2 = self.set_builder("sidebar", TestBuilder)

        app = App()
        new_data = Bag()
        new_data["key"] = "value"
        app.reactive_store = new_data

        assert app.b1.data is app.reactive_store
        assert app.b2.data is app.reactive_store
        assert app.b1.data["key"] == "value"

    def test_data_setter_accepts_dict(self):
        """Manager.data setter converts dict to Bag."""

        class App(BuilderManager):
            def __init__(self):
                pass

        app = App()
        app.reactive_store = {"name": "test"}
        assert isinstance(app.reactive_store, Bag)
        assert app.reactive_store["name"] == "test"


class TestManagerBuild:
    """Tests for build (materializes all builders)."""

    def test_build(self):
        """build() materializes all registered builders."""

        class App(BuilderManager):
            def __init__(self):
                self.b1 = self.set_builder("page", TestBuilder)
                self.b2 = self.set_builder("sidebar", TestBuilder)

        app = App()
        app.b1.source.heading("Page")
        app.b2.source.heading("Sidebar")
        app.build()

        assert "Page" in app.b1.render()
        assert "Sidebar" in app.b2.render()


class TestManagerBuilderProperties:
    """Tests for builder created via manager."""

    def test_builder_has_source(self):
        """Builder created via manager has source property."""

        class App(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", TestBuilder)

        app = App()
        assert app.page.source is not None

    def test_builder_has_built(self):
        """Builder created via manager has built property."""

        class App(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", TestBuilder)

        app = App()
        assert app.page.built is not None

    def test_builder_source_accepts_elements(self):
        """Can populate source with builder elements."""

        class App(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", TestBuilder)

        app = App()
        app.page.source.heading("Hello")
        assert len(app.page.source) == 1


class TestManagerRun:
    """Tests for BuilderManager.run() convenience method."""

    def test_run_calls_setup_and_build(self):
        """run() calls setup() and build() in sequence."""

        class App(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", TestBuilder)
                self.run()

            def store(self, data):
                data["title"] = "Hello"

            def main(self, source):
                source.heading(value="^title")

        app = App()
        assert "Hello" in app.page.render()

    def test_run_produces_same_result_as_manual_sequence(self):
        """run() produces identical result to manual setup+build."""

        class ManualApp(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", TestBuilder)
                self.setup()
                self.build()

            def main(self, source):
                source.heading("Test")

        class RunApp(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", TestBuilder)
                self.run()

            def main(self, source):
                source.heading("Test")

        manual = ManualApp()
        run_app = RunApp()
        assert manual.page.render() == run_app.page.render()

    def test_no_subscribe_method(self):
        """BuilderManager does not have subscribe() — use ReactiveManager."""
        assert "subscribe" not in BuilderManager.__dict__

    def test_run_has_no_subscribe_param(self):
        """BuilderManager.run() does not accept a subscribe parameter."""
        import inspect as _inspect

        sig = _inspect.signature(BuilderManager.run)
        assert "subscribe" not in sig.parameters


class TestStandaloneBuilder:
    """Tests for builder without manager."""

    def test_standalone_builder(self):
        """Builder instantiated without arguments has own pipeline."""
        builder = TestBuilder()
        assert builder.source is not None
        assert builder.built is not None
        assert builder.data is not None

    def test_standalone_data_is_own(self):
        """Standalone builder has its own data, not proxied."""
        builder = TestBuilder()
        builder.data["key"] = "value"
        assert builder.data["key"] == "value"

    def test_standalone_source_accepts_elements(self):
        """Standalone builder source accepts elements."""
        builder = TestBuilder()
        builder.source.heading("Hello")
        assert len(builder.source) == 1

    def test_standalone_data_replacement(self):
        """Standalone builder data setter works."""
        builder = TestBuilder()
        new_data = Bag()
        new_data["name"] = "Alice"
        builder.data = new_data
        assert builder.data["name"] == "Alice"

    def test_standalone_data_from_dict(self):
        """Standalone builder data setter converts dict."""
        builder = TestBuilder()
        builder.data = {"name": "Bob"}
        assert isinstance(builder.data, Bag)
        assert builder.data["name"] == "Bob"
