# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Volume routing tests (Tranche B, Fase 5).

A pointer of the form ``volume:path`` resolves the volume part to
``manager.resolve_volume(name)`` and routes the read/write to that
builder's local_store. ``BuiltBagNode.{get,set}_relative_data`` and
``BuilderBagNode.{get,set}_relative_data`` perform this routing
transparently. Build-time data elements (``data_setter``,
``data_formula``) flow through the same channel.
"""

from __future__ import annotations

import asyncio

from genro_builders import BuilderManager
from tests.helpers import TestBuilder as _Builder


class _MultiApp(BuilderManager):
    """Two builders: a 'page' and a 'data' volume."""

    def on_init(self) -> None:
        self.page = self.register_builder("page", _Builder)
        self.data = self.register_builder("data", _Builder)


def _maybe_run(result: object) -> None:
    if asyncio.iscoroutine(result):
        asyncio.run(result)


def _first_built_node(builder: object) -> object:
    """Return the first node of the builder's built bag."""
    return next(iter(builder.built))  # type: ignore[attr-defined]


class TestRelativeDataVolumeRouting:
    """``BuiltBagNode.{get,set}_relative_data`` routes via volume prefix."""

    def test_set_relative_data_routes_to_volume(self) -> None:
        app = _MultiApp()
        app.page.source.heading(value="x")
        _maybe_run(app.page.build())

        node = _first_built_node(app.page)
        node.set_relative_data("data:customer.name", "Acme")

        assert app.resolve_volume("data").get_item("customer.name") == "Acme"

    def test_get_relative_data_routes_to_volume(self) -> None:
        app = _MultiApp()
        app.resolve_volume("data")["customer.name"] = "Acme"
        app.page.source.heading(value="x")
        _maybe_run(app.page.build())

        node = _first_built_node(app.page)
        assert node.get_relative_data("data:customer.name") == "Acme"

    def test_volume_without_manager_raises(self) -> None:
        """Standalone builder cannot resolve volumes — there's no registry."""
        builder = _Builder()
        builder.source.heading(value="x")
        _maybe_run(builder.build())

        node = _first_built_node(builder)
        try:
            node.get_relative_data("other:foo")
        except RuntimeError as exc:
            assert "no manager" in str(exc)
        else:
            raise AssertionError("expected RuntimeError")


class TestDataSetterWithVolume:
    """``data_setter`` writes route through the manager registry."""

    def test_data_setter_with_volume_path(self) -> None:
        app = _MultiApp()
        app.page.source.data_setter("data:theme", value="dark")
        _maybe_run(app.page.build())

        assert app.resolve_volume("data").get_item("theme") == "dark"
        # The page's own local_store must NOT carry the volume-prefixed key.
        assert app.resolve_volume("page").get_item("data:theme") is None

    def test_data_setter_local_path_writes_to_own_store(self) -> None:
        app = _MultiApp()
        app.page.source.data_setter("title", value="Hello")
        _maybe_run(app.page.build())

        assert app.resolve_volume("page").get_item("title") == "Hello"


class TestDataFormulaWithVolumeDep:
    """``data_formula`` resolves dependency pointers across volumes."""

    def test_formula_reads_from_remote_volume(self) -> None:
        app = _MultiApp()
        app.resolve_volume("data")["price"] = 50
        app.page.source.data_formula(
            "total",
            func=lambda price: price * 2,
            price="^data:price",
            _on_built=True,
        )
        _maybe_run(app.page.build())

        assert app.resolve_volume("page").get_item("total") == 100

    def test_formula_writes_to_remote_volume(self) -> None:
        """A formula installed on ``volume:path`` lives on the volume's
        local_store, not on the local builder.
        """
        app = _MultiApp()
        app.resolve_volume("page")["price"] = 7
        app.page.source.data_formula(
            "data:double",
            func=lambda x: x * 2,
            x="^price",
            _on_built=True,
        )
        _maybe_run(app.page.build())

        assert app.resolve_volume("data").get_item("double") == 14
        assert app.resolve_volume("page").get_item("data:double") is None


class TestBuilderBagNodeParity:
    """``BuilderBagNode.current_from_datasource`` honours volume routing."""

    def test_current_from_datasource_volume(self) -> None:
        app = _MultiApp()
        app.resolve_volume("data")["customer.name"] = "Acme"

        # Use a source-side node and resolve a volume pointer.
        # We need a node anchored under 'page' to call current_from_datasource.
        node = app.page.source.heading()
        result = node.current_from_datasource("^data:customer.name", app.page.data)

        assert result == "Acme"
