# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Manager registry tests.

Covers the registry-based manager API: ``local_store(name)``,
``resolve_volume(name)``, and the invariant
``manager.local_store(name) is builder._data``.

Also asserts that no monolithic data store exists on the manager —
the previous ``global_store`` and ``_data`` attributes have been
removed.
"""

from __future__ import annotations

import pytest

from genro_builders import BuilderManager
from tests.helpers import TestBuilder as _Builder


class _App(BuilderManager):
    def on_init(self) -> None:
        self.register_builder("page", _Builder)
        self.register_builder("sidebar", _Builder)


class TestLocalStoreRegistry:
    """``local_store`` returns the builder's private ``_data`` Bag."""

    def test_local_store_returns_builder_private_bag(self) -> None:
        app = _App()
        assert app.local_store("page") is app._builders["page"]._data

    def test_resolve_volume_alias_of_local_store(self) -> None:
        app = _App()
        assert app.resolve_volume("page") is app.local_store("page")
        assert app.resolve_volume("sidebar") is app.local_store("sidebar")

    def test_local_store_unknown_builder_raises_keyerror(self) -> None:
        app = _App()
        with pytest.raises(KeyError, match="not registered"):
            app.local_store("missing")

    def test_resolve_volume_unknown_raises_keyerror(self) -> None:
        app = _App()
        with pytest.raises(KeyError, match="not registered"):
            app.resolve_volume("missing")

    def test_local_store_no_context_no_arg_raises_runtimeerror(self) -> None:
        app = _App()
        with pytest.raises(RuntimeError, match="no current builder context"):
            app.local_store()

    def test_local_store_during_main_dispatch_uses_current(self) -> None:
        captured: dict[str, object] = {}

        class App(BuilderManager):
            def on_init(self) -> None:
                self.register_builder("a", _Builder)
                self.register_builder("b", _Builder)

            def main_a(self, source):
                captured["a"] = self.local_store()

            def main_b(self, source):
                captured["b"] = self.local_store()

        app = App()
        app.setup()
        assert captured["a"] is app._builders["a"]._data
        assert captured["b"] is app._builders["b"]._data


class TestNoMonolithicStore:
    """The manager exposes no monolithic data store."""

    def test_no_global_store_attribute(self) -> None:
        app = _App()
        assert not hasattr(app, "global_store")

    def test_no_underscore_data_attribute(self) -> None:
        app = _App()
        assert not hasattr(app, "_data")

    def test_stores_registry_holds_each_builder_data(self) -> None:
        app = _App()
        assert app._stores["page"] is app._builders["page"]._data
        assert app._stores["sidebar"] is app._builders["sidebar"]._data


class TestBuilderDataIsPrivate:
    """``builder.data`` always returns the private ``_data`` Bag."""

    def test_builder_data_is_private_bag_when_managed(self) -> None:
        app = _App()
        page = app._builders["page"]
        assert page.data is page._data

    def test_builder_data_setter_clears_in_place(self) -> None:
        app = _App()
        page = app._builders["page"]
        original = page._data
        page.data = {"title": "hello"}
        assert page._data is original
        assert page.data is original
        assert page.data.get_item("title") == "hello"

    def test_resolve_volume_reflects_builder_data_writes(self) -> None:
        """Writes via ``builder.data`` are visible via
        ``manager.resolve_volume(name)`` because both handles are the
        same Bag object.
        """
        app = _App()
        page = app._builders["page"]
        page.data["title"] = "x"
        assert app.resolve_volume("page").get_item("title") == "x"
