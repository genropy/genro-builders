# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for ComponentProxy — component value on source node, tree constraint."""
from __future__ import annotations

import pytest

from genro_builders import BagBuilderBase, ComponentProxy
from genro_builders.builder import component, element
from genro_builders.builder_bag import BuilderBag as Bag


class TestComponentProxy:
    """Component call returns a ComponentProxy set as node.value."""

    def test_component_returns_proxy(self):
        class B(BagBuilderBase):
            @component()
            def myform(self, comp, main_kwargs=None):
                return comp

        bag = Bag(builder=B)
        result = bag.myform()
        assert isinstance(result, ComponentProxy)

    def test_source_node_has_is_component_flag(self):
        class B(BagBuilderBase):
            @component()
            def myform(self, comp, main_kwargs=None):
                return comp

        bag = Bag(builder=B)
        bag.myform()
        node = bag.get_node("myform_0")
        assert node.attr.get("_is_component") is True

    def test_source_node_value_is_proxy(self):
        class B(BagBuilderBase):
            @component()
            def myform(self, comp, main_kwargs=None):
                return comp

        bag = Bag(builder=B)
        bag.myform()
        node = bag.get_node("myform_0")
        assert isinstance(node.value, ComponentProxy)

    def test_handler_not_called_at_creation(self):
        called = False

        class B(BagBuilderBase):
            @component()
            def myform(self, comp, main_kwargs=None):
                nonlocal called
                called = True
                return comp

        bag = Bag(builder=B)
        bag.myform()
        assert not called


class TestTreeConstraint:
    """A component must produce exactly one top-level node."""

    def test_zero_top_level_raises(self):
        class B(BagBuilderBase):
            @component()
            def empty(self, comp, main_kwargs=None):
                _ = comp

        bag = Bag(builder=B)
        bag.empty()
        node = bag.get_node("empty_0")

        with pytest.raises(ValueError, match="must produce a single top-level node"):
            bag._builder._expand_component(node.value)

    def test_two_top_level_raises(self):
        class B(BagBuilderBase):
            @element()
            def field(self): ...

            @component()
            def forest(self, comp, main_kwargs=None):
                comp.field()
                comp.field()

        bag = Bag(builder=B)
        bag.forest()
        node = bag.get_node("forest_0")

        with pytest.raises(ValueError, match="must produce a single top-level node"):
            bag._builder._expand_component(node.value)

    def test_main_tag_mismatch_raises(self):
        class B(BagBuilderBase):
            @element()
            def field(self): ...

            @element()
            def other(self): ...

            @component(main_tag="field")
            def mismatch(self, comp, main_kwargs=None):
                comp.other()

        bag = Bag(builder=B)
        bag.mismatch()
        node = bag.get_node("mismatch_0")

        with pytest.raises(ValueError, match="declared main_tag"):
            bag._builder._expand_component(node.value)

    def test_single_top_level_ok(self):
        class B(BagBuilderBase):
            @element()
            def field(self): ...

            @component()
            def single(self, comp, main_kwargs=None):
                comp.field(value="x")

        bag = Bag(builder=B)
        bag.single()
        node = bag.get_node("single_0")

        expanded = bag._builder._expand_component(node.value)
        assert len(expanded) == 1

    def test_main_tag_match_ok(self):
        class B(BagBuilderBase):
            @element()
            def field(self): ...

            @component(main_tag="field")
            def matched(self, comp, main_kwargs=None):
                comp.field(value="x")

        bag = Bag(builder=B)
        bag.matched()
        node = bag.get_node("matched_0")

        expanded = bag._builder._expand_component(node.value)
        top = next(iter(expanded))
        assert top.node_tag == "field"


class TestBasedOn:
    """Component inheritance via based_on."""

    def test_based_on_simple(self):
        class B(BagBuilderBase):
            @element()
            def item(self): ...

            @component(main_tag="item")
            def base_row(self, comp, main_kwargs=None):
                comp.item(value="base")

            @component(main_tag="item", based_on="base_row")
            def extended_row(self, comp, main_kwargs=None):
                _ = comp

        bag = Bag(builder=B)
        bag.extended_row()
        node = bag.get_node("extended_row_0")

        expanded = bag._builder._expand_component(node.value)
        assert len(expanded) == 1
        top = next(iter(expanded))
        assert top.attr.get("value") == "base"
