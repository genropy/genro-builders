# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for ReactiveManager — BuilderManager with reactive bindings."""
from __future__ import annotations

from genro_builders.manager import BuilderManager, ReactiveManager

from .helpers import TestBuilder


class TestReactiveManagerBasics:
    """ReactiveManager extends BuilderManager with subscribe()."""

    def test_is_subclass_of_builder_manager(self):
        """ReactiveManager is a BuilderManager subclass."""
        assert issubclass(ReactiveManager, BuilderManager)

    def test_has_subscribe(self):
        """ReactiveManager has subscribe() method."""
        assert hasattr(ReactiveManager, "subscribe")
        assert callable(ReactiveManager.subscribe)

    def test_run_accepts_subscribe_param(self):
        """ReactiveManager.run() accepts a subscribe parameter."""
        import inspect as _inspect

        sig = _inspect.signature(ReactiveManager.run)
        assert "subscribe" in sig.parameters


class TestReactiveManagerRun:
    """Tests for ReactiveManager.run() with subscribe support."""

    def test_run_without_subscribe(self):
        """run() without subscribe works like BuilderManager.run()."""

        class App(ReactiveManager):
            def on_init(self):
                self.page = self.register_builder("page", TestBuilder)
                self.run()

            def store(self, data):
                data["title"] = "Hello"

            def main(self, source):
                source.heading(value="^title")

        app = App()
        assert "Hello" in app.page.render()

    def test_run_with_subscribe(self):
        """run(subscribe=True) activates reactive bindings."""

        class App(ReactiveManager):
            def on_init(self):
                self.page = self.register_builder("page", TestBuilder)
                self.run(subscribe=True)

            def store(self, data):
                data["title"] = "Hello"

            def main(self, source):
                source.heading(value="^title")

        app = App()
        # After subscribe, changing data triggers re-render
        app.reactive_store["title"] = "Updated"
        assert "Updated" in app.page.render()


class TestReactiveManagerSubscribe:
    """Tests for ReactiveManager.subscribe() directly."""

    def test_subscribe_activates_bindings(self):
        """subscribe() enables reactive data propagation."""

        class App(ReactiveManager):
            def on_init(self):
                self.page = self.register_builder("page", TestBuilder)
                self.setup()
                self.build()
                self.subscribe()

            def store(self, data):
                data["title"] = "Original"

            def main(self, source):
                source.heading(value="^title")

        app = App()
        app.reactive_store["title"] = "Changed"
        assert "Changed" in app.page.render()

    def test_manual_sequence_matches_run_subscribe(self):
        """Manual setup+build+subscribe matches run(subscribe=True)."""

        class ManualApp(ReactiveManager):
            def on_init(self):
                self.page = self.register_builder("page", TestBuilder)
                self.setup()
                self.build()
                self.subscribe()

            def main(self, source):
                source.heading("Test")

        class RunApp(ReactiveManager):
            def on_init(self):
                self.page = self.register_builder("page", TestBuilder)
                self.run(subscribe=True)

            def main(self, source):
                source.heading("Test")

        manual = ManualApp()
        run_app = RunApp()
        assert manual.page.render() == run_app.page.render()
