# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for output methods: introspection, check, compile, documentation,
SchemaBuilder compile/meta, render_value, and string representation."""

import pytest

from genro_builders import BagBuilderBase
from genro_builders.builder import SchemaBuilder
from genro_builders.builder_bag import BuilderBag as Bag
from genro_builders.builders import abstract, element


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
# Tests for builder._compile()
# =============================================================================


class TestBuilderCompile:
    """Tests for builder._compile() output method.

    NOTE: Output format tests are suspended pending full compile workflow definition.
    Only testing that compile() is callable and raises for unknown format.
    """

    @pytest.mark.skip(reason="Compile output format TBD - workflow da definire")
    def test_compile_defaults_to_xml(self):
        """compile() defaults to XML format."""

        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        bag.item("content")

        result = bag.builder._compile()
        # XML uses tag name, not label
        assert "<item" in result
        assert "content" in result

    @pytest.mark.skip(reason="Compile output format TBD - workflow da definire")
    def test_compile_xml_format(self):
        """compile(format='xml') produces valid XML."""

        class Builder(BagBuilderBase):
            @element()
            def div(self): ...

        bag = Bag(builder=Builder)
        bag.div("hello")

        result = bag.builder._compile(format="xml")
        assert result.startswith("<")
        # XML uses tag name
        assert "<div" in result

    @pytest.mark.skip(reason="Compile output format TBD - workflow da definire")
    def test_compile_json_format(self):
        """compile(format='json') produces JSON."""

        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        bag.item("value")

        result = bag.builder._compile(format="json")
        assert "item_0" in result
        assert "value" in result

    def test_compile_unknown_format_raises(self):
        """compile() raises ValueError for unknown format."""

        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        bag.item()

        with pytest.raises(ValueError, match="Unknown format"):
            bag.builder._compile(format="yaml")

    def test_compile_is_callable(self):
        """compile() is callable on builder."""

        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        bag.item("content")

        # Just verify it's callable and returns something
        result = bag.builder._compile()
        assert result is not None


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
# Tests for schema_to_md()
# =============================================================================


class TestSchemaToMd:
    """Tests for schema_to_md() method."""

    def test_schema_to_md_basic(self):
        """schema_to_md() generates markdown with elements."""

        class Builder(BagBuilderBase):
            @element()
            def button(self):
                """A clickable button."""
                ...

            @element(sub_tags="span,p")
            def div(self):
                """A container element."""
                ...

        bag = Bag(builder=Builder)
        md = bag.builder._schema_to_md()

        assert "# Schema: Builder" in md
        assert "## Elements" in md
        assert "`button`" in md
        assert "`div`" in md
        assert "A clickable button." in md
        assert "A container element." in md

    def test_schema_to_md_with_abstracts(self):
        """schema_to_md() includes abstract elements section."""

        class Builder(BagBuilderBase):
            @abstract(sub_tags="span,p")
            def flow(self):
                """Flow content model."""
                ...

            @element(inherits_from="@flow")
            def div(self): ...

        bag = Bag(builder=Builder)
        md = bag.builder._schema_to_md()

        assert "## Abstract Elements" in md
        assert "`@flow`" in md
        assert "Flow content model." in md
        assert "## Elements" in md
        assert "`div`" in md

    def test_schema_to_md_with_meta(self):
        """schema_to_md() shows _meta."""

        class Builder(BagBuilderBase):
            @element(_meta={"compile_module": "textual.widgets", "compile_class": "Button"})
            def button(self): ...

        bag = Bag(builder=Builder)
        md = bag.builder._schema_to_md()

        assert "compile_module: textual.widgets" in md
        assert "compile_class: Button" in md

    def test_schema_to_md_custom_title(self):
        """schema_to_md() accepts custom title."""

        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        md = bag.builder._schema_to_md(title="My Custom Builder")

        assert "# Schema: My Custom Builder" in md

    def test_schema_to_md_table_format(self):
        """schema_to_md() generates valid markdown tables."""

        class Builder(BagBuilderBase):
            @element(sub_tags="item")
            def container(self):
                """Container element."""
                ...

            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        md = bag.builder._schema_to_md()

        # Check table structure
        assert "| Name |" in md
        assert "| --- |" in md
        assert "| `container` |" in md
        assert "| `item` |" in md


# =============================================================================
# Tests for SchemaBuilder.compile
# =============================================================================


class TestSchemaBuilderCompile:
    """Tests for SchemaBuilder.compile method."""

    def test_compile_saves_msgpack(self, tmp_path):
        """SchemaBuilder.compile saves schema to msgpack file."""
        schema = Bag(builder=SchemaBuilder)
        schema.builder.item("div", sub_tags="span")
        schema.builder.item("span")

        # Use correct extension for msgpack files
        output_file = tmp_path / "test_schema.bag.mp"
        schema.builder._compile(output_file)

        # File should exist and contain msgpack data
        assert output_file.exists()
        assert output_file.stat().st_size > 0

        # Should be loadable
        loaded = Bag().fill_from(output_file)
        assert loaded.get_node("div") is not None
        assert loaded.get_node("span") is not None


# =============================================================================
# Tests for _render_value
# =============================================================================


class TestRenderValue:
    """Tests for _render_value method."""

    def test_value_format_attribute(self):
        """_render_value applies value_format from node attribute.

        value_format is a Python format string applied to the node value.
        The format uses .format() method, so for numeric formatting we need {}.
        """

        class Builder(BagBuilderBase):
            @element()
            def price(self): ...

        bag = Bag(builder=Builder)
        # Use format that adds prefix/suffix
        bag.price(node_value="42.50", value_format="Price: {}")

        node = bag.get_node("price_0")
        result = bag.builder._render_value(node)

        assert result == "Price: 42.50"

    def test_value_template_attribute(self):
        """_render_value applies value_template from node attribute."""

        class Builder(BagBuilderBase):
            @element()
            def greeting(self): ...

        bag = Bag(builder=Builder)
        bag.greeting(node_value="World", value_template="Hello, {node_value}!")

        node = bag.get_node("greeting_0")
        result = bag.builder._render_value(node)

        assert result == "Hello, World!"

    def test_meta_callback(self):
        """_render_value calls _meta callback to modify context."""

        class Builder(BagBuilderBase):
            @element(_meta={"callback": "uppercase_value"})
            def loud(self): ...

            def uppercase_value(self, ctx):
                ctx["node_value"] = ctx["node_value"].upper()

        bag = Bag(builder=Builder)
        bag.loud(node_value="hello")

        node = bag.get_node("loud_0")
        result = bag.builder._render_value(node)

        assert result == "HELLO"

    def test_meta_format_schema(self):
        """_render_value applies _meta format from schema."""

        class Builder(BagBuilderBase):
            @element(_meta={"format": "[{}]"})
            def bracketed(self): ...

        bag = Bag(builder=Builder)
        bag.bracketed(node_value="content")

        node = bag.get_node("bracketed_0")
        result = bag.builder._render_value(node)

        assert result == "[content]"

    def test_default_value_in_template_context(self):
        """_render_value uses parameter default values, not base types.

        call_args_validations tuples are (base_type, validators, default).
        The template context must receive the default VALUE, not the type.
        """
        import inspect

        class Builder(BagBuilderBase):
            @element()
            def card(self, color: str = "red", border: int = 2): ...

        bag = Bag(builder=Builder)
        # Build a card WITHOUT passing color or border
        bag.card(node_value="Hello")

        node = bag.get_node("card_0")
        result_ctx = {}
        # Simulate what _render_value does: extract defaults from schema
        tag = node.node_tag or node.label
        info = bag.builder._get_schema_info(tag)
        call_args = info.get("call_args_validations") or {}
        for param_name, (base_type, _validators, default) in call_args.items():
            if default is not None and default is not inspect.Parameter.empty:
                result_ctx[param_name] = default

        # Must receive the default VALUES, not the type objects
        assert result_ctx["color"] == "red"
        assert result_ctx["border"] == 2
        assert result_ctx["color"] != str
        assert result_ctx["border"] != int


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
