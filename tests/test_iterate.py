# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for the iterate capability — call-time and build-time invariants.

Covers contract §8.1 (component-only) and §8.2 (cardinality + non-Bag
target). Tests for the full set of iterate use cases (replication,
datapath shape, data binding, mutation) live elsewhere — this file pins
the two new TypeError gates introduced together with §8."""
from __future__ import annotations

import asyncio

import pytest

from genro_builders.builder import BagBuilderBase, component, element


class _Iter(BagBuilderBase):
    """Minimal builder with a container, an item element, and a card component."""

    @element(sub_tags="*")
    def container(self): ...

    @element(sub_tags="")
    def item(self): ...

    @element(sub_tags="")
    def box(self): ...

    @component(main_tag="box", sub_tags="")
    def card(self, comp, main_kwargs=None):
        comp.box(**(main_kwargs or {}))


def _maybe_run(result: object) -> None:
    if asyncio.iscoroutine(result):
        asyncio.run(result)


# ---------------------------------------------------------------------------
# Call-time gate (contract §8.1)
# ---------------------------------------------------------------------------


class TestIterateCallTimeGate:
    """``iterate`` is component-only; using it on an @element raises at the call."""

    def test_iterate_on_element_raises(self):
        builder = _Iter()
        with pytest.raises(TypeError, match="iterate requires a @component"):
            builder.source.item(iterate="^items")


# ---------------------------------------------------------------------------
# Build-time cardinality (contract §8.2)
# ---------------------------------------------------------------------------


class TestIterateCardinality:
    """N→N replicas; non-Bag target raises; missing path or empty Bag → 0."""

    def test_iterate_on_non_bag_target_raises(self):
        builder = _Iter()
        builder.data["payload"] = "not a bag"
        root = builder.source.container(datapath="root")
        root.card(iterate="^payload")
        with pytest.raises(TypeError, match="iterate target must be a Bag"):
            _maybe_run(builder.build())

    def test_iterate_on_missing_path_yields_zero(self):
        builder = _Iter()
        root = builder.source.container(datapath="ghost")
        root.card(iterate="^.")
        _maybe_run(builder.build())

        # The container is the only top-level node; it must have no children
        # because the iterated path does not exist.
        container_node = next(iter(builder.built))
        assert len(container_node.value) == 0

    def test_iterate_on_empty_bag_yields_zero(self):
        builder = _Iter()
        from genro_bag import Bag
        builder.data["items"] = Bag()
        root = builder.source.container(datapath="items")
        root.card(iterate="^.")
        _maybe_run(builder.build())

        container_node = next(iter(builder.built))
        assert len(container_node.value) == 0
