# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for main()/store() pattern on standalone builders."""
from __future__ import annotations

from .helpers import TestBuilder


class TestMainStore:
    """Tests for main/store pattern on standalone builder."""

    def test_main_populates_source(self):
        """Subclass main() is called to populate source."""

        class MyBuilder(TestBuilder):
            def main(self, source):
                source.heading("from main")

        b = MyBuilder()
        b.build()
        assert "from main" in b.output

    def test_store_populates_data(self):
        """Subclass store() populates data before main."""

        class MyBuilder(TestBuilder):
            def store(self, data):
                data["msg"] = "hello"

            def main(self, source):
                source.heading(value="^msg")

        b = MyBuilder()
        b.build()
        assert "hello" in b.output

    def test_store_called_before_main(self):
        """store() is called before main()."""
        order = []

        class MyBuilder(TestBuilder):
            def store(self, data):
                order.append("store")

            def main(self, source):
                order.append("main")
                source.heading("test")

        b = MyBuilder()
        b.build()
        assert order == ["store", "main"]

    def test_no_main_no_store_still_works(self):
        """Builder without main/store works as before (manual population)."""
        b = TestBuilder()
        b.source.heading("manual")
        b.build()
        assert "manual" in b.output

    def test_main_with_helpers(self):
        """main() can call helper methods on self."""

        class MyBuilder(TestBuilder):
            def main(self, source):
                self.header(source)
                self.body(source)

            def header(self, source):
                source.heading("header")

            def body(self, source):
                source.text("body")

        b = MyBuilder()
        b.build()
        assert "header" in b.output
        assert "body" in b.output

    def test_store_only_no_main(self):
        """Only store() without main() — user populates manually."""

        class MyBuilder(TestBuilder):
            def store(self, data):
                data["title"] = "Hello"

        b = MyBuilder()
        b.source.heading(value="^title")
        b.build()
        assert "Hello" in b.output
