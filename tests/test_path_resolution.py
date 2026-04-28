# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Path resolution tests — the five canonical pointer forms.

Covers ``docs/builders/manager-architecture.md`` §5–§6:

    'field'                 — absolute in the builder's local_store.
    '.field'                — relative, resolved via the ancestor chain.
    'volume:field'          — absolute in another builder's local_store.
    '#node_id.field'        — symbolic (source-side only).
    'volume:#node_id.field' — symbolic across volumes.

Tests exercise the user-facing API (``get_relative_data``,
``set_relative_data``, ``data_setter``), and assert the contract's
no-silent-fallback rule by triggering ``ValueError`` / ``KeyError``
through the same public surface.
"""

from __future__ import annotations

import asyncio

import pytest

from genro_builders import BuilderManager
from genro_builders.builder import BagBuilderBase, element


class _Container(BagBuilderBase):
    """Minimal builder with one nestable element."""

    @element(sub_tags="*")
    def container(self): ...

    @element(sub_tags="")
    def item(self): ...


def _maybe_run(result: object) -> None:
    if asyncio.iscoroutine(result):
        asyncio.run(result)


# ---------------------------------------------------------------------------
# Form 1 — absolute (plain) and Form 2 — relative
# ---------------------------------------------------------------------------


class TestAbsoluteAndRelative:
    """Plain and relative pointers resolve against the builder's local_store."""

    def test_absolute_pointer_reads_own_local_store(self) -> None:
        builder = _Container()
        builder.data["title"] = "Hello"
        builder.source.item(value="^title")
        _maybe_run(builder.build())

        node = next(iter(builder.built))
        assert node.runtime_attrs["value"] == "Hello"

    def test_relative_pointer_resolves_via_ancestor_datapath(self) -> None:
        builder = _Container()
        builder.data["customer.name"] = "Acme"
        c = builder.source.container(datapath="customer")
        c.item(value="^.name")
        _maybe_run(builder.build())

        # The container is the only top-level node; descend to its child.
        container_node = next(iter(builder.built))
        item_node = next(iter(container_node.value))
        assert item_node.runtime_attrs["value"] == "Acme"

    def test_relative_pointer_chains_nested_datapaths(self) -> None:
        builder = _Container()
        builder.data["app.user.email"] = "u@example.com"
        outer = builder.source.container(datapath="app")
        inner = outer.container(datapath=".user")
        inner.item(value="^.email")
        _maybe_run(builder.build())

        outer_node = next(iter(builder.built))
        inner_node = next(iter(outer_node.value))
        item_node = next(iter(inner_node.value))
        assert item_node.runtime_attrs["value"] == "u@example.com"

    def test_relative_without_anchor_raises(self) -> None:
        """No silent fallback: a relative pointer with no datapath
        anchor in the chain must surface a ValueError, not return None.
        """
        builder = _Container()
        node = builder.source.item("x")

        with pytest.raises(ValueError, match="without a datapath context"):
            node.abs_datapath(".name")

    def test_relative_chain_without_absolute_anchor_raises(self) -> None:
        """Chain with ONLY relative datapaths (no absolute anchor anywhere)
        must surface a ValueError. A relative datapath like ``.r0`` is never
        promoted to an anchor by stripping its leading dot. Contract §5.1
        / invariant #16 (no hidden automatisms).
        """
        builder = _Container()
        outer = builder.source.container(datapath=".r0")  # relative
        inner = outer.container(datapath=".child")        # relative
        leaf = inner.item("x")

        with pytest.raises(ValueError, match="without a datapath context"):
            leaf.abs_datapath(".name")


# ---------------------------------------------------------------------------
# Form 3 — volume:path
# ---------------------------------------------------------------------------


class _CrossApp(BuilderManager):
    """Two builders. ``page`` reads/writes ``data:foo`` cross-builder."""

    def on_init(self) -> None:
        self.page = self.register_builder("page", _Container)
        self.data = self.register_builder("data", _Container)


class TestVolumePointer:
    """``volume:path`` routes to the named builder's local_store."""

    def test_volume_pointer_reads_remote_local_store(self) -> None:
        app = _CrossApp()
        app.resolve_volume("data")["customer.name"] = "Acme"

        app.page.source.item(value="^data:customer.name")
        _maybe_run(app.page.build())

        node = next(iter(app.page.built))
        assert node.runtime_attrs["value"] == "Acme"

    def test_data_setter_with_volume_writes_remote(self) -> None:
        app = _CrossApp()
        app.page.source.data_setter("data:theme", value="dark")
        _maybe_run(app.page.build())

        # Remote store has the value; the local store does not.
        assert app.resolve_volume("data").get_item("theme") == "dark"
        assert app.resolve_volume("page").get_item("data:theme") is None

    def test_unknown_volume_raises(self) -> None:
        app = _CrossApp()
        app.page.source.item(value="^missing:foo")
        _maybe_run(app.page.build())

        node = next(iter(app.page.built))
        with pytest.raises(KeyError, match="not registered"):
            _ = node.runtime_attrs

    def test_volume_without_manager_raises(self) -> None:
        """Standalone builder cannot resolve volumes — no registry."""
        builder = _Container()
        builder.data["foo"] = 1
        builder.source.item(value="^other:foo")
        _maybe_run(builder.build())

        node = next(iter(builder.built))
        with pytest.raises(RuntimeError, match="no manager"):
            _ = node.runtime_attrs


# ---------------------------------------------------------------------------
# Form 4 — #node_id (symbolic, source-side only)
# ---------------------------------------------------------------------------


class TestSymbolicPointer:
    """``#node_id.field`` resolves via the source-side node_id map."""

    def test_symbolic_resolves_to_node_datapath(self) -> None:
        builder = _Container()
        builder.source.container(node_id="addr", datapath="customer.address")
        node = builder.source.item("x")

        assert node.abs_datapath("#addr.street") == "customer.address.street"

    def test_symbolic_without_suffix_returns_node_datapath(self) -> None:
        builder = _Container()
        builder.source.container(node_id="addr", datapath="customer.address")
        node = builder.source.item("x")

        assert node.abs_datapath("#addr") == "customer.address"

    def test_symbolic_unknown_id_raises(self) -> None:
        builder = _Container()
        node = builder.source.item("x")

        with pytest.raises(KeyError):
            node.abs_datapath("#nonexistent.foo")
