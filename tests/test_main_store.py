# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for main()/store() pattern via BuilderManager."""
from __future__ import annotations

from genro_builders.manager import BuilderManager

from .helpers import TestBuilder


class TestMainStore:
    """Tests for main/store pattern on BuilderManager."""

    def test_main_populates_source(self):
        """Subclass main() is called to populate source."""

        class App(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", TestBuilder)

            def main(self, source):
                source.heading("from main")

        app = App()
        app.setup()
        app.build()
        assert "from main" in app.page.render()

    def test_store_populates_data(self):
        """Subclass store() populates data before main."""

        class App(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", TestBuilder)

            def store(self, data):
                data["msg"] = "hello"

            def main(self, source):
                source.heading(value="^msg")

        app = App()
        app.setup()
        app.build()
        assert "hello" in app.page.render()

    def test_store_called_before_main(self):
        """store() is called before main()."""
        order = []

        class App(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", TestBuilder)

            def store(self, data):
                order.append("store")

            def main(self, source):
                order.append("main")
                source.heading("test")

        app = App()
        app.setup()
        app.build()
        assert order == ["store", "main"]

    def test_no_main_no_store_still_works(self):
        """Manager without main/store works (manual population)."""

        class App(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", TestBuilder)

        app = App()
        app.page.source.heading("manual")
        app.build()
        assert "manual" in app.page.render()

    def test_main_with_helpers(self):
        """main() can call helper methods on self."""

        class App(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", TestBuilder)

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

    def test_store_only_no_main(self):
        """Only store() without main() — user populates source manually."""

        class App(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", TestBuilder)

            def store(self, data):
                data["title"] = "Hello"

        app = App()
        app.setup()
        app.page.source.heading(value="^title")
        app.build()
        assert "Hello" in app.page.render()
