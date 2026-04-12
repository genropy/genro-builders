# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for output methods: introspection, check, compile, documentation,
SchemaBuilder compile/meta, render_value, and string representation."""

import pytest

from genro_builders import BagBuilderBase
from genro_builders.builder import SchemaBuilder
from genro_builders.builder_bag import BuilderBag as Bag
from genro_builders.builder import abstract, element


# =============================================================================
# Tests for builder introspection
# =============================================================================


class TestBuilderIntrospection:
    """Tests for builder introspection methods."""

    def test_repr_shows_element_count(self):
        """__repr__ shows element count."""

        class Builder(BagBuilderBase):
            @element()
            def div(self): ...

            @element()
            def span(self): ...

            @abstract(sub_tags="div,span")
            def flow(self): ...

        bag = Bag(builder=Builder)
        repr_str = repr(bag.builder)

        assert "Builder" in repr_str
        assert "6 elements" in repr_str  # div, span, @flow + 3 data_elements

    def test_get_schema_info_raises_on_unknown(self):
        """get_schema_info raises KeyError for unknown element."""

        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        with pytest.raises(KeyError, match="not found"):
            bag.builder._get_schema_info("unknown")

    def test_getattr_raises_on_unknown_element(self):
        """Accessing unknown element raises AttributeError."""

        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        with pytest.raises(AttributeError, match="has no attribute 'unknown'"):
            bag.unknown()


# =============================================================================
# Tests for builder._check()
# =============================================================================


class TestBuilderCheck:
    """Tests for builder._check() validation method."""

    def test_check_empty_bag_returns_empty_list(self):
        """check() on empty bag returns empty list."""

        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        result = bag.builder._check()
        assert result == []

    def test_check_valid_bag_returns_empty_list(self):
        """check() on valid bag returns empty list."""

        class Builder(BagBuilderBase):
            @element(sub_tags="inner")
            def outer(self): ...

            @element(sub_tags="")
            def inner(self): ...

        bag = Bag(builder=Builder)
        outer_node = bag.outer()
        outer_node.inner()

        result = bag.builder._check()
        assert result == []

    def test_check_finds_invalid_nodes(self):
        """check() finds nodes with missing required children."""

        class Builder(BagBuilderBase):
            @element(sub_tags="required[1]")
            def container(self): ...

            @element(sub_tags="")
            def required(self): ...

        bag = Bag(builder=Builder)
        bag.container()  # Missing required child

        result = bag.builder._check()
        assert len(result) == 1
        path, node, reasons = result[0]
        assert "container_0" in path
        assert "required" in reasons

    def test_check_walks_nested_bags(self):
        """check() recursively walks nested Bag structures."""

        class Builder(BagBuilderBase):
            @element(sub_tags="middle")
            def wrapper(self): ...

            @element(sub_tags="leaf[1]")
            def middle(self): ...

            @element(sub_tags="")
            def leaf(self): ...

        bag = Bag(builder=Builder)
        wrapper_node = bag.wrapper()
        wrapper_node.middle()  # Missing required leaf

        result = bag.builder._check()
        assert len(result) == 1
        path, node, reasons = result[0]
        assert "middle" in path
        assert "leaf" in reasons

    def test_check_accepts_explicit_bag(self):
        """check() can validate an explicit bag parameter."""

        class Builder(BagBuilderBase):
            @element(sub_tags="inner[1]")
            def outer(self): ...

            @element(sub_tags="")
            def inner(self): ...

        bag = Bag(builder=Builder)
        bag.outer()  # Missing required child

        other_bag = Bag(builder=Builder)
        outer_node = other_bag.outer()
        outer_node.inner()  # Valid

        # Check the invalid bag explicitly
        result = bag.builder._check(bag)
        assert len(result) == 1

        # Check the valid bag explicitly
        result = bag.builder._check(other_bag)
        assert result == []


# =============================================================================
# Tests for builder.validate()
# =============================================================================


class TestBuilderValidate:
    """Tests for builder.validate() public validation method."""

    def test_validate_returns_empty_list_for_valid_bag(self):
        """validate() on valid bag returns empty list."""

        class Builder(BagBuilderBase):
            @element(sub_tags="inner")
            def outer(self): ...

            @element(sub_tags="")
            def inner(self): ...

        bag = Bag(builder=Builder)
        outer_node = bag.outer()
        outer_node.inner()

        result = bag.builder.validate()
        assert result == []

    def test_validate_returns_dict_format_with_path_tag_reasons(self):
        """validate() returns list of dicts with path, tag, reasons keys."""

        class Builder(BagBuilderBase):
            @element(sub_tags="required[1]")
            def container(self): ...

            @element(sub_tags="")
            def required(self): ...

        bag = Bag(builder=Builder)
        bag.container()  # Missing required child

        result = bag.builder.validate()
        assert len(result) == 1
        err = result[0]
        assert "path" in err
        assert "tag" in err
        assert "reasons" in err
        assert "container_0" in err["path"]
        assert isinstance(err["reasons"], list)

    def test_validate_walks_nested_bags(self):
        """validate() recursively walks nested Bag structures."""

        class Builder(BagBuilderBase):
            @element(sub_tags="middle")
            def wrapper(self): ...

            @element(sub_tags="leaf[1]")
            def middle(self): ...

            @element(sub_tags="")
            def leaf(self): ...

        bag = Bag(builder=Builder)
        wrapper_node = bag.wrapper()
        wrapper_node.middle()  # Missing required leaf

        result = bag.builder.validate()
        assert len(result) == 1
        assert "middle" in result[0]["path"]
        assert "leaf" in result[0]["reasons"]

    def test_validate_accepts_explicit_bag_argument(self):
        """validate() can validate an explicit bag parameter."""

        class Builder(BagBuilderBase):
            @element(sub_tags="inner[1]")
            def outer(self): ...

            @element(sub_tags="")
            def inner(self): ...

        bag = Bag(builder=Builder)
        bag.outer()  # Missing required child

        other_bag = Bag(builder=Builder)
        outer_node = other_bag.outer()
        outer_node.inner()  # Valid

        assert len(bag.builder.validate(bag)) == 1
        assert bag.builder.validate(other_bag) == []


# =============================================================================
# Tests for SchemaBuilder _meta
# =============================================================================


class TestSchemaBuilderMeta:
    """Tests for _meta in SchemaBuilder.item()."""

    def test_schema_builder_item_meta_dict(self):
        """SchemaBuilder.item() with _meta dict stores in schema."""
        schema = Bag(builder=SchemaBuilder)
        schema.builder.item("widget", _meta={"compile_module": "textual.widgets", "compile_class": "Button"})

        info = schema.get_attr("widget")
        assert info["_meta"] == {"compile_module": "textual.widgets", "compile_class": "Button"}

    def test_schema_builder_item_without_meta(self):
        """SchemaBuilder.item() without _meta has no _meta."""
        schema = Bag(builder=SchemaBuilder)
        schema.builder.item("simple", sub_tags="child")

        info = schema.get_attr("simple")
        assert "_meta" not in info or info.get("_meta") is None


# =============================================================================
# Tests for documentation extraction
# =============================================================================


class TestDocumentation:
    """Tests for documentation extraction from decorated methods."""

    def test_element_docstring_stored_in_schema(self):
        """@element method docstring is saved as documentation in schema."""

        class Builder(BagBuilderBase):
            @element()
            def button(self):
                """A clickable button element."""
                ...

        info = Builder._class_schema.get_attr("button")
        assert info["documentation"] == "A clickable button element."

    def test_element_no_docstring_has_none(self):
        """@element method without docstring has documentation=None."""

        class Builder(BagBuilderBase):
            @element()
            def simple(self): ...

        info = Builder._class_schema.get_attr("simple")
        assert info.get("documentation") is None

    def test_abstract_docstring_stored_in_schema(self):
        """@abstract method docstring is saved as documentation in schema."""

        class Builder(BagBuilderBase):
            @abstract(sub_tags="child")
            def container(self):
                """Base container for layout elements."""
                ...

        info = Builder._class_schema.get_attr("@container")
        assert info["documentation"] == "Base container for layout elements."

    def test_schema_builder_documentation_param(self):
        """SchemaBuilder.item() with documentation param stores in schema."""
        schema = Bag(builder=SchemaBuilder)
        schema.builder.item("widget", documentation="A generic widget element.")

        info = schema.get_attr("widget")
        assert info["documentation"] == "A generic widget element."

    def test_schema_builder_no_documentation(self):
        """SchemaBuilder.item() without documentation has None."""
        schema = Bag(builder=SchemaBuilder)
        schema.builder.item("simple")

        info = schema.get_attr("simple")
        assert info.get("documentation") is None

    def test_get_schema_info_includes_documentation(self):
        """get_schema_info() returns documentation from schema."""

        class Builder(BagBuilderBase):
            @element()
            def input(self):
                """Text input field."""
                ...

        bag = Bag(builder=Builder)
        info = bag.builder._get_schema_info("input")
        assert info["documentation"] == "Text input field."


# =============================================================================
# Tests for SchemaBuilder.save_schema
# =============================================================================


class TestSchemaBuilderSaveSchema:
    """Tests for SchemaBuilder.save_schema method."""

    def test_save_schema_writes_msgpack(self, tmp_path):
        """SchemaBuilder.save_schema saves schema to msgpack file."""
        schema = Bag(builder=SchemaBuilder)
        schema.builder.item("div", sub_tags="span")
        schema.builder.item("span")

        # Use correct extension for msgpack files
        output_file = tmp_path / "test_schema.bag.mp"
        schema.builder.save_schema(output_file)

        # File should exist and contain msgpack data
        assert output_file.exists()
        assert output_file.stat().st_size > 0

        # Should be loadable
        loaded = Bag().fill_from(output_file)
        assert loaded.get_node("div") is not None
        assert loaded.get_node("span") is not None


# =============================================================================
# Tests for builder __str__ and __iter__
# =============================================================================


class TestBuilderStringRepresentation:
    """Tests for builder __str__ and __iter__."""

    def test_builder_str(self):
        """Builder __str__ returns schema structure."""

        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        result = str(bag.builder)

        # Should include schema node
        assert "item" in result

    def test_builder_iter(self):
        """Builder __iter__ iterates over schema nodes."""

        class Builder(BagBuilderBase):
            @element()
            def alpha(self): ...

            @element()
            def beta(self): ...

        bag = Bag(builder=Builder)
        tags = [node.label for node in bag.builder]

        assert "alpha" in tags
        assert "beta" in tags
