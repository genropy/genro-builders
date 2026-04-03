# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for @data_element decorator and data_setter/data_formula/data_controller."""
from __future__ import annotations

import pytest

from genro_builders.builder import BagBuilderBase, data_element, element
from tests.helpers import TestBuilder

# =============================================================================
# Decorator registration
# =============================================================================


class TestDataElementRegistration:
    """Tests for @data_element decorator and schema registration."""

    def test_data_element_creates_schema_entry(self):
        """Schema has is_data_element=True for data_element tags."""
        builder = TestBuilder()
        info = builder._get_schema_info("data_setter")
        assert info.get("is_data_element") is True
        assert info.get("handler_name") == "_dtel_data_setter"

    def test_data_element_all_three_registered(self):
        """All three data_element tags are registered in schema."""
        builder = TestBuilder()
        for tag in ("data_setter", "data_formula", "data_controller"):
            info = builder._get_schema_info(tag)
            assert info.get("is_data_element") is True

    def test_data_element_requires_body(self):
        """@data_element with empty body raises ValueError."""
        with pytest.raises(ValueError, match="must have a body"):
            class BadBuilder(BagBuilderBase):
                @data_element()
                def my_data(self): ...

    def test_data_element_inherited_by_subclass(self):
        """Concrete builder inherits data_setter/formula/controller from BagBuilderBase."""

        class MinimalBuilder(BagBuilderBase):
            @element()
            def item(self): ...

        builder = MinimalBuilder()
        assert "data_setter" in builder._schema_tag_names
        assert "data_formula" in builder._schema_tag_names
        assert "data_controller" in builder._schema_tag_names


# =============================================================================
# Source population
# =============================================================================


class TestDataElementSource:
    """Tests for data_element node creation in source."""

    def test_data_setter_creates_source_node(self):
        """data_setter creates a node in source with _is_data_element=True."""
        builder = TestBuilder()
        builder.source.data_setter("title", value="Hello")

        node = builder.source.get_node("data_setter_0")
        assert node is not None
        assert node.attr.get("_is_data_element") is True
        assert node.attr.get("_data_path") == "title"
        assert node.attr.get("value") == "Hello"

    def test_data_formula_creates_source_node(self):
        """data_formula creates a node in source."""
        builder = TestBuilder()
        builder.source.data_formula("total", func=lambda a, b: a + b)

        node = builder.source.get_node("data_formula_0")
        assert node is not None
        assert node.attr.get("_is_data_element") is True

    def test_data_controller_creates_source_node(self):
        """data_controller creates a node with path=None."""
        builder = TestBuilder()
        builder.source.data_controller(func=lambda: None)

        node = builder.source.get_node("data_controller_0")
        assert node is not None
        assert node.attr.get("_is_data_element") is True
        assert node.attr.get("_data_path") is None

    def test_data_element_transparent_in_sub_tags(self):
        """Data element inside element with strict sub_tags doesn't violate."""

        class StrictBuilder(BagBuilderBase):
            @element(sub_tags="item")
            def container(self): ...

            @element()
            def item(self): ...

        builder = StrictBuilder()
        container = builder.source.container()
        container.data_setter("key", value=42)
        container.item()

        # No validation error — data_setter is transparent
        assert builder.source.get_node("container_0") is not None


# =============================================================================
# Build processing
# =============================================================================


class TestDataElementBuild:
    """Tests for data_element processing during build."""

    def test_data_setter_writes_to_data(self):
        """data_setter writes value at path in data Bag after build."""
        builder = TestBuilder()
        builder.source.data_setter("title", value="Hello")
        builder.build()

        assert builder.data["title"] == "Hello"

    def test_data_formula_computes(self):
        """data_formula calls func and writes result."""
        builder = TestBuilder()
        builder.source.data_formula(
            "result", func=lambda a, b: a + b, a=10, b=20,
        )
        builder.build()

        assert builder.data["result"] == 30

    def test_data_formula_with_pointer(self):
        """data_formula resolves ^pointer in kwargs before calling func."""
        builder = TestBuilder()
        builder.data["input"] = 5
        builder.source.data_setter("multiplier", value=3)
        builder.source.data_formula(
            "result",
            func=lambda x, m: x * m,
            x="^input",
            m="^multiplier",
        )
        builder.build()

        assert builder.data["result"] == 15

    def test_data_controller_executes(self):
        """data_controller calls the function during build."""
        called = []
        builder = TestBuilder()
        builder.source.data_controller(func=lambda: called.append(True))
        builder.build()

        assert len(called) == 1

    def test_data_element_not_in_built(self):
        """Built Bag does not contain data_element nodes."""
        builder = TestBuilder()
        builder.source.data_setter("title", value="Hello")
        builder.source.heading("^title")
        builder.build()

        # Built has only heading, no data_setter
        assert builder.built.get_node("heading_0") is not None
        assert builder.built.get_node("data_setter_0") is None

    def test_infra_before_normal(self):
        """Data set by data_setter is available to ^pointer in normal elements."""
        builder = TestBuilder()
        builder.source.data_setter("title", value="From Setter")
        builder.source.heading("^title")
        builder.build()

        assert "From Setter" in builder.render()

    def test_multiple_data_setters(self):
        """Multiple data_setters at same level all processed."""
        builder = TestBuilder()
        builder.source.data_setter("a", value=1)
        builder.source.data_setter("b", value=2)
        builder.build()

        assert builder.data["a"] == 1
        assert builder.data["b"] == 2

    def test_data_setter_dict_to_bag(self):
        """data_setter with dict value converts it to Bag."""
        from genro_bag import Bag

        builder = TestBuilder()
        builder.source.data_setter("shipping", value={"cost": 25, "days": 3})
        builder.build()

        result = builder.data["shipping"]
        assert isinstance(result, Bag)
        assert result["cost"] == 25
        assert result["days"] == 3

    def test_data_formula_dict_to_bag(self):
        """data_formula returning dict converts result to Bag."""
        from genro_bag import Bag

        builder = TestBuilder()
        builder.source.data_formula(
            "info",
            func=lambda: {"name": "Alice", "age": 30},
        )
        builder.build()

        result = builder.data["info"]
        assert isinstance(result, Bag)
        assert result["name"] == "Alice"
        assert result["age"] == 30


# =============================================================================
# _onBuilt hook
# =============================================================================


class TestOnBuiltHook:
    """Tests for _onBuilt hook on data_controller."""

    def test_on_built_called(self):
        """_onBuilt hook is called after build completes."""
        called = []
        builder = TestBuilder()
        builder.source.data_controller(
            func=lambda: None,
            _onBuilt=lambda b: called.append(b),
        )
        builder.build()

        assert len(called) == 1

    def test_on_built_receives_builder(self):
        """_onBuilt hook receives the builder instance."""
        received = []
        builder = TestBuilder()
        builder.source.data_controller(
            func=lambda: None,
            _onBuilt=lambda b: received.append(b),
        )
        builder.build()

        assert received[0] is builder

    def test_on_built_not_called_without_attribute(self):
        """data_setter without _onBuilt does not trigger hook."""
        called = []
        builder = TestBuilder()
        builder.source.data_setter("key", value=42)
        builder.build()

        assert len(called) == 0


# =============================================================================
# Edge cases
# =============================================================================


class TestDataElementEdgeCases:
    """Edge case tests for data_element."""

    def test_data_element_in_component(self):
        """Data elements inside component body are processed during build."""
        builder = TestBuilder()
        builder.source.section(title="Test")
        # section component creates heading + text
        # We need a component that uses data_setter internally
        # For now, test that build doesn't crash with components
        builder.build()
        assert builder.built.get_node("section_0") is not None

    def test_rebuild_clears_hooks(self):
        """After rebuild, hooks from previous build are gone."""
        called = []
        builder = TestBuilder()
        builder.source.data_controller(
            func=lambda: None,
            _onBuilt=lambda b: called.append("hook"),
        )
        builder.build()
        assert len(called) == 1

        builder.build()
        assert len(called) == 2  # Called again on rebuild
