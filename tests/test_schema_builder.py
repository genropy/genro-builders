# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for SchemaBuilder — programmatic schema creation."""

import pytest

from genro_builders.builder import SchemaBuilder
from genro_builders.builder_bag import BuilderBag as Bag


class TestSchemaBuilderItem:
    """Tests for SchemaBuilder.item() element creation."""

    def test_item_creates_element(self):
        """item() creates a schema element accessible by name."""
        schema = Bag(builder=SchemaBuilder)
        schema.builder.item("div")
        assert schema.get_node("div") is not None

    def test_item_with_sub_tags(self):
        """item() stores sub_tags on the schema node."""
        schema = Bag(builder=SchemaBuilder)
        schema.builder.item("ul", sub_tags="li")
        info = schema.get_attr("ul")
        assert info["sub_tags"] == "li"

    def test_item_with_empty_sub_tags(self):
        """sub_tags='' creates a void element (no children allowed)."""
        schema = Bag(builder=SchemaBuilder)
        schema.builder.item("br", sub_tags="")
        info = schema.get_attr("br")
        assert info["sub_tags"] == ""

    def test_item_with_wildcard_sub_tags(self):
        """sub_tags='*' allows any children."""
        schema = Bag(builder=SchemaBuilder)
        schema.builder.item("div", sub_tags="*")
        info = schema.get_attr("div")
        assert info["sub_tags"] == "*"

    def test_item_with_cardinality_sub_tags(self):
        """sub_tags with cardinality syntax is stored correctly."""
        schema = Bag(builder=SchemaBuilder)
        schema.builder.item("html", sub_tags="head[:1],body[:1]")
        info = schema.get_attr("html")
        assert info["sub_tags"] == "head[:1],body[:1]"

    def test_item_with_parent_tags(self):
        """parent_tags restricts where the element can appear."""
        schema = Bag(builder=SchemaBuilder)
        schema.builder.item("li", parent_tags="ul,ol")
        info = schema.get_attr("li")
        assert info["parent_tags"] == "ul,ol"

    def test_item_with_inherits_from(self):
        """inherits_from references an abstract element."""
        schema = Bag(builder=SchemaBuilder)
        schema.builder.item("@flow", sub_tags="p,span")
        schema.builder.item("div", inherits_from="@flow")
        info = schema.get_attr("div")
        assert info["inherits_from"] == "@flow"

    def test_item_with_documentation(self):
        """documentation string is stored on the schema node."""
        schema = Bag(builder=SchemaBuilder)
        schema.builder.item("section", documentation="A page section.")
        info = schema.get_attr("section")
        assert info["documentation"] == "A page section."

    def test_item_with_meta(self):
        """_meta dict is stored on the schema node."""
        schema = Bag(builder=SchemaBuilder)
        meta = {"tag_template": "<{tag}>{value}</{tag}>"}
        schema.builder.item("p", _meta=meta)
        info = schema.get_attr("p")
        assert info["_meta"] == meta

    def test_item_with_call_args_validations(self):
        """call_args_validations is stored on the schema node."""
        schema = Bag(builder=SchemaBuilder)
        validations = {"color": (str, [], "red")}
        schema.builder.item("card", call_args_validations=validations)
        info = schema.get_attr("card")
        assert info["call_args_validations"] == validations

    def test_item_returns_bag_node(self):
        """item() returns the created BagNode."""
        schema = Bag(builder=SchemaBuilder)
        node = schema.builder.item("div")
        assert node is not None
        assert node.label == "div"

    def test_multiple_items(self):
        """Multiple items can be created in sequence."""
        schema = Bag(builder=SchemaBuilder)
        schema.builder.item("div", sub_tags="p,span")
        schema.builder.item("p")
        schema.builder.item("span")
        assert schema.get_node("div") is not None
        assert schema.get_node("p") is not None
        assert schema.get_node("span") is not None

    def test_abstract_prefixed_with_at(self):
        """Abstract elements use @ prefix convention."""
        schema = Bag(builder=SchemaBuilder)
        schema.builder.item("@phrasing", sub_tags="span,em,strong")
        assert schema.get_node("@phrasing") is not None

    def test_unknown_element_returns_none(self):
        """Accessing unknown element returns None from get_node."""
        schema = Bag(builder=SchemaBuilder)
        schema.builder.item("div")
        assert schema.get_node("unknown") is None


class TestSchemaBuilderCompile:
    """Tests for SchemaBuilder._compile() round-trip."""

    def test_compile_creates_file(self, tmp_path):
        """_compile() creates a .bag.mp file."""
        schema = Bag(builder=SchemaBuilder)
        schema.builder.item("doc", sub_tags="section,paragraph")
        schema.builder.item("section", sub_tags="paragraph")
        schema.builder.item("paragraph")

        dest = tmp_path / "schema.bag.mp"
        schema.builder._compile(dest)
        assert dest.exists()
        assert dest.stat().st_size > 0

    def test_compile_preserves_attributes(self, tmp_path):
        """Compiled schema preserves element attributes."""
        schema = Bag(builder=SchemaBuilder)
        schema.builder.item("doc", sub_tags="section", documentation="The root.")
        schema.builder.item("section", parent_tags="doc")

        dest = tmp_path / "schema.bag.mp"
        schema.builder._compile(dest)

        # Reload and verify attributes survived
        from genro_bag import Bag as RawBag

        loaded = RawBag.from_tytx(dest.read_bytes(), transport="msgpack")
        doc_node = loaded.get_node("doc")
        assert doc_node is not None
        assert doc_node.attr.get("sub_tags") == "section"
        assert doc_node.attr.get("documentation") == "The root."

        section_node = loaded.get_node("section")
        assert section_node is not None
        assert section_node.attr.get("parent_tags") == "doc"
