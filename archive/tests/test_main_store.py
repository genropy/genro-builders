# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for main() pattern via BuilderManager."""
from __future__ import annotations

from genro_builders.manager import BuilderManager

from .helpers import TestBuilder


class TestMainStore:
    """Tests for main pattern on BuilderManager."""

    def test_main_populates_source(self):
        """Subclass main() is called to populate source."""

        class App(BuilderManager):
            def on_init(self):
                self.page = self.register_builder("page", TestBuilder)

            def main(self, source):
                source.heading("from main")

        app = App()
        app.setup()
        app.build()
        assert "from main" in app.page.render()

    def test_data_populated_in_main(self):
        """Data can be populated inside main() via local_store."""

        class App(BuilderManager):
            def on_init(self):
                self.page = self.register_builder("page", TestBuilder)

            def main(self, source):
                self.local_store()["msg"] = "hello"
                source.heading(value="^msg")

        app = App()
        app.setup()
        app.build()
        assert "hello" in app.page.render()

    def test_no_main_still_works(self):
        """Manager without main works (manual population)."""

        class App(BuilderManager):
            def on_init(self):
                self.page = self.register_builder("page", TestBuilder)

        app = App()
        app.page.source.heading("manual")
        app.build()
        assert "manual" in app.page.render()

    def test_main_with_helpers(self):
        """main() can call helper methods on self."""

        class App(BuilderManager):
            def on_init(self):
                self.page = self.register_builder("page", TestBuilder)

            def main(self, source):
                self.header(source)
                self.body(source)

            def header(self, source):
                source.heading("header")

            def body(self, source):
                source.text("body")

        app = App()
        app.setup()
        app.build()
        output = app.page.render()
        assert "header" in output
        assert "body" in output

    def test_data_only_no_main(self):
        """Data populated before setup — user populates source manually."""

        class App(BuilderManager):
            def on_init(self):
                self.page = self.register_builder("page", TestBuilder)

        app = App()
        app.local_store("page")["title"] = "Hello"
        app.setup()
        app.page.source.heading(value="^title")
        app.build()
        assert "Hello" in app.page.render()

    def test_local_store_in_main(self):
        """local_store() works inside main() dispatch."""

        class App(BuilderManager):
            def on_init(self):
                self.page = self.register_builder("page", TestBuilder)

            def main(self, source):
                self.local_store()["title"] = "From local"
                source.heading("test")

        app = App()
        app.setup()
        assert app.global_store["page.title"] == "From local"

    def test_local_store_with_name(self):
        """local_store(name) returns the named builder's namespace."""

        class App(BuilderManager):
            def on_init(self):
                self.page = self.register_builder("page", TestBuilder)
                self.sidebar = self.register_builder("sidebar", TestBuilder)

            def main_page(self, source):
                self.local_store("sidebar")["color"] = "blue"
                source.heading("test")

            def main_sidebar(self, source):
                source.heading("test")

        app = App()
        app.setup()
        assert app.global_store["sidebar.color"] == "blue"
