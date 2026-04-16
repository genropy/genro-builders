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

            def main(self, source):
                self.local_store()["title"] = "Hello"
                source.heading(value="^title")

        app = App()
        assert "Hello" in app.page.render()

    def test_run_with_subscribe(self):
        """run(subscribe=True) activates reactive bindings."""

        class App(ReactiveManager):
            def on_init(self):
                self.page = self.register_builder("page", TestBuilder)
                self.run(subscribe=True)

            def main(self, source):
                self.local_store()["title"] = "Hello"
                source.heading(value="^title")

        app = App()
        # After subscribe, changing data triggers re-render
        app.local_store("page")["title"] = "Updated"
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

            def main(self, source):
                self.local_store()["title"] = "Original"
                source.heading(value="^title")

        app = App()
        app.local_store("page")["title"] = "Changed"
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


class TestReactiveNotification:
    """Tests for the data change notification chain (Phase 2)."""

    def test_on_data_changed_fires_on_data_change(self):
        """Changing data after subscribe fires on_data_changed."""
        notifications = []

        class App(ReactiveManager):
            def on_init(self):
                self.page = self.register_builder("page", TestBuilder)
                self.run(subscribe=True)

            def main(self, source):
                self.local_store()["title"] = "Hello"
                source.heading(value="^title")

            def on_data_changed(self, impacted):
                notifications.append(impacted)

        app = App()
        # Change data — in sync context, flush is immediate
        app.local_store("page")["title"] = "Updated"
        assert len(notifications) >= 1
        assert "page" in notifications[-1]

    def test_on_data_changed_not_fired_without_subscribe(self):
        """Without subscribe, no notification fires."""
        notifications = []

        class App(ReactiveManager):
            def on_init(self):
                self.page = self.register_builder("page", TestBuilder)
                self.run()  # no subscribe

            def main(self, source):
                self.local_store()["title"] = "Hello"
                source.heading(value="^title")

            def on_data_changed(self, impacted):
                notifications.append(impacted)

        app = App()
        app.local_store("page")["title"] = "Updated"
        assert len(notifications) == 0

    def test_on_data_changed_receives_correct_builder(self):
        """The impacted dict contains the correct builder name."""
        notifications = []

        class App(ReactiveManager):
            def on_init(self):
                self.page = self.register_builder("page", TestBuilder)
                self.run(subscribe=True)

            def main(self, source):
                self.local_store()["title"] = "Hello"
                source.heading(value="^title")

            def on_data_changed(self, impacted):
                notifications.append(impacted)

        app = App()
        app.local_store("page")["title"] = "Changed"
        assert notifications[-1] == {"page": "render"}

    def test_on_data_changed_with_formula_chain(self):
        """Formula chain: price → total → heading. Notifies page."""
        notifications = []

        class App(ReactiveManager):
            def on_init(self):
                self.page = self.register_builder("page", TestBuilder)
                self.run(subscribe=True)

            def main(self, source):
                self.local_store()["price"] = 100
                source.data_formula(
                    "total", func=lambda price: price * 2, price="^price",
                )
                source.heading(value="^total")

            def on_data_changed(self, impacted):
                notifications.append(impacted)

        app = App()
        app.local_store("page")["price"] = 200
        assert any("page" in n for n in notifications)

    def test_unrelated_data_change_no_notification(self):
        """Data change on an unrelated path does not notify builders."""
        notifications = []

        class App(ReactiveManager):
            def on_init(self):
                self.page = self.register_builder("page", TestBuilder)
                self.run(subscribe=True)

            def main(self, source):
                self.local_store()["title"] = "Hello"
                source.heading(value="^title")

            def on_data_changed(self, impacted):
                notifications.append(impacted)

        app = App()
        # Change a path that no builder depends on
        app.global_store.set_item("unrelated", 42)
        assert len(notifications) == 0

    def test_dispatching_guard_prevents_reentry(self):
        """Writing to data store inside on_data_changed does not loop."""
        call_count = [0]

        class App(ReactiveManager):
            def on_init(self):
                self.page = self.register_builder("page", TestBuilder)
                self.run(subscribe=True)

            def main(self, source):
                self.local_store()["count"] = 0
                source.heading(value="^count")

            def on_data_changed(self, impacted):
                call_count[0] += 1
                # Write to data store inside callback — should not loop
                self.local_store("page")["count"] = call_count[0]

        app = App()
        app.local_store("page")["count"] = 1
        # Should fire once, not infinitely
        assert call_count[0] >= 1
        assert call_count[0] < 5  # sanity check: no infinite loop

    def test_unsubscribe_stops_notifications(self):
        """After unsubscribe, no more notifications."""
        notifications = []

        class App(ReactiveManager):
            def on_init(self):
                self.page = self.register_builder("page", TestBuilder)
                self.run(subscribe=True)

            def main(self, source):
                self.local_store()["x"] = 1
                source.heading(value="^x")

            def on_data_changed(self, impacted):
                notifications.append(impacted)

        app = App()
        app.local_store("page")["x"] = 2
        count_before = len(notifications)
        app.unsubscribe()
        app.local_store("page")["x"] = 3
        assert len(notifications) == count_before

    def test_multi_builder_targeted_notification(self):
        """Only impacted builders appear in notification."""
        notifications = []

        class App(ReactiveManager):
            def on_init(self):
                self.a = self.register_builder("a", TestBuilder)
                self.b = self.register_builder("b", TestBuilder)
                self.run(subscribe=True)

            def main_a(self, source):
                self.local_store()["color"] = "red"
                source.heading(value="^color")

            def main_b(self, source):
                self.local_store()["size"] = 10
                source.heading(value="^size")

            def on_data_changed(self, impacted):
                notifications.append(impacted)

        app = App()
        # Change only builder a's data
        app.local_store("a")["color"] = "blue"
        assert any("a" in n and "b" not in n for n in notifications)
