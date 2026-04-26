# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Manager registry tests (Tranche B, Fase 1).

Covers the registry-based manager API: ``local_store(name)``,
``resolve_volume(name)`` and the alias guarantee that
``manager.local_store(name) is builder._data``.

Compat tests for the still-living monolithic ``_data`` are kept here
until Fase 3 removes ``global_store``; they are renamed/removed at
that point.
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


class TestRegisterBuilderAliases:
    """Compat invariant: ``_data["<name>"]`` aliases ``builder._data``.

    Both handles point to the same Bag object — writes through one are
    visible through the other. The monolithic ``_data`` is removed in
    Fase 3; this test will be replaced at that point.
    """

    def test_register_builder_aliases_global_store_entry(self) -> None:
        app = _App()
        assert app.global_store.get_item("page") is app.local_store("page")
        assert app.global_store.get_item("sidebar") is app.local_store("sidebar")


class TestBuilderDataIsPrivate:
    """Fase 2: ``builder.data`` always returns the private ``_data`` Bag."""

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

    def test_global_store_reflects_builder_data_writes(self) -> None:
        """Compat alias holds: writes via ``builder.data`` show up in
        ``global_store["<name>"]`` because the two handles are the
        same Bag object.
        """
        app = _App()
        page = app._builders["page"]
        page.data["title"] = "x"
        assert app.global_store.get_item("page.title") == "x"
