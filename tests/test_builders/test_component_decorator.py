# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for @component decorator - STRUCTURE tests only.

Tests cover:
- @component decorator creates schema entry with handler_name
- sub_tags='' returns parent bag (closed/leaf)
- sub_tags defined or absent returns internal bag (open/container)
- parent_tags validation works same as element
- SchemaBuilder cannot use @component (code-based only)
- @component requires real body (not ellipsis)
- kwargs validation on component

NOTE: Tests for component EXPANSION (body called, bag populated, nested components)
are in tests/test_compilers/test_component_expansion.py
"""

import pytest

from genro_builders import BagBuilderBase
from genro_builders.builder import SchemaBuilder
from genro_builders.builder_bag import BuilderBag as Bag
from genro_builders.builders import component, element


# =============================================================================
# Basic @component decorator tests - SCHEMA STRUCTURE
# =============================================================================


class TestComponentDecoratorSchema:
    """Tests for @component decorator schema registration."""

    def test_component_creates_schema_entry(self):
        """@component creates entry in schema with handler_name."""

        class Builder(BagBuilderBase):
            @component()
            def myform(self, comp: Bag, **kwargs):
                comp.field()
                return comp

            @element()
            def field(self): ...

            @element()
            def div(self): ...

        # Schema should have myform
        node = Builder._class_schema.get_node("myform")
        assert node is not None
        # Components use handler_name instead of adapter_name
        assert node.attr.get("handler_name") is not None

    def test_component_marked_as_component_in_schema(self):
        """@component sets is_component=True in schema."""

        class Builder(BagBuilderBase):
            @component()
            def myform(self, comp: Bag, **kwargs):
                return comp

        node = Builder._class_schema.get_node("myform")
        assert node.attr.get("is_component") is True

    def test_component_sub_tags_in_schema(self):
        """@component sub_tags are stored in schema."""

        class Builder(BagBuilderBase):
            @component(sub_tags="item,field")
            def myform(self, comp: Bag, **kwargs):
                return comp

        node = Builder._class_schema.get_node("myform")
        assert node.attr.get("sub_tags") == "item,field"

    def test_component_void_sub_tags_in_schema(self):
        """@component sub_tags='' (void) is stored correctly."""

        class Builder(BagBuilderBase):
            @component(sub_tags="")
            def closed_form(self, comp: Bag, **kwargs):
                return comp

        node = Builder._class_schema.get_node("closed_form")
        assert node.attr.get("sub_tags") == ""


# =============================================================================
# Tests for sub_tags return behavior - STRUCTURE (no expansion verification)
# =============================================================================


class TestComponentSubTagsReturnBehavior:
    """Tests for sub_tags controlling return value at CALL time."""

    def test_void_sub_tags_returns_parent(self):
        """sub_tags='' (void) returns parent bag for chaining at same level."""

        class Builder(BagBuilderBase):
            @component(sub_tags="")
            def closed_form(self, comp: Bag, **kwargs):
                return comp

            @element()
            def span(self): ...

        bag = Bag(builder=Builder)
        result = bag.closed_form()

        # Should return parent bag (root in this case)
        assert result is bag
        # Can continue at same level
        result.span()
        assert len(bag) == 2  # closed_form + span

    def test_defined_sub_tags_returns_parent_bag(self):
        """All components return parent bag for chaining."""

        class Builder(BagBuilderBase):
            @component(sub_tags="item")
            def mylist(self, comp: Bag, **kwargs):
                return comp

            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        result = bag.mylist()

        # All components return parent bag for chaining
        assert result is bag

    def test_absent_sub_tags_returns_parent_bag(self):
        """No sub_tags (absent) returns parent bag for chaining."""

        class Builder(BagBuilderBase):
            @component()
            def container(self, comp: Bag, **kwargs):
                return comp

            @element()
            def anything(self): ...

        bag = Bag(builder=Builder)
        result = bag.container()

        # All components return parent bag
        assert result is bag

    def test_none_sub_tags_returns_parent_bag(self):
        """sub_tags=None explicitly returns parent bag for chaining."""

        class Builder(BagBuilderBase):
            @component(sub_tags=None)
            def container(self, comp: Bag, **kwargs):
                return comp

            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        result = bag.container()

        # All components return parent bag
        assert result is bag


# =============================================================================
# Tests for parent_tags validation
# =============================================================================


class TestComponentParentTags:
    """Tests for parent_tags validation on components."""

    def test_valid_parent_allowed(self):
        """Component with parent_tags can be placed in valid parent."""

        class Builder(BagBuilderBase):
            @element(sub_tags="myform")
            def div(self): ...

            @component(sub_tags="", parent_tags="div")
            def myform(self, comp: Bag, **kwargs):
                return comp

        bag = Bag(builder=Builder)
        div = bag.div()
        div.myform()  # Should not raise

        assert len(div.value) == 1

    def test_invalid_parent_rejected(self):
        """Component with parent_tags cannot be placed in invalid parent."""

        class Builder(BagBuilderBase):
            @element(sub_tags="myform,span")
            def div(self): ...

            @element(sub_tags="myform")
            def section(self): ...

            @component(sub_tags="", parent_tags="section")
            def myform(self, comp: Bag, **kwargs):
                return comp

            @element()
            def span(self): ...

        bag = Bag(builder=Builder)
        div = bag.div()

        with pytest.raises(ValueError, match="parent_tags requires"):
            div.myform()  # div is not valid parent

    def test_parent_tags_at_root_rejected(self):
        """Component with parent_tags cannot be placed at root."""

        class Builder(BagBuilderBase):
            @element(sub_tags="myform")
            def container(self): ...

            @component(sub_tags="", parent_tags="container")
            def myform(self, comp: Bag, **kwargs):
                return comp

        bag = Bag(builder=Builder)

        with pytest.raises(ValueError, match="parent_tags requires"):
            bag.myform()  # root not valid

    def test_multiple_parent_tags(self):
        """Component can have multiple valid parents."""

        class Builder(BagBuilderBase):
            @element(sub_tags="myform")
            def div(self): ...

            @element(sub_tags="myform")
            def section(self): ...

            @component(sub_tags="", parent_tags="div, section")
            def myform(self, comp: Bag, **kwargs):
                return comp

        bag = Bag(builder=Builder)

        div = bag.div()
        div.myform()  # OK

        section = bag.section()
        section.myform()  # OK

        assert len(div.value) == 1
        assert len(section.value) == 1


# =============================================================================
# Tests for SchemaBuilder restrictions
# =============================================================================


class TestSchemaBuilderCannotUseComponent:
    """Tests that SchemaBuilder cannot use @component decorator."""

    def test_schema_builder_no_component_method(self):
        """SchemaBuilder does not have component() method."""
        schema = Bag(builder=SchemaBuilder)

        # SchemaBuilder should not have component capability
        with pytest.raises(AttributeError):
            schema.component()

    def test_component_requires_code_handler(self):
        """@component decorator requires actual code - ellipsis not allowed."""

        with pytest.raises((ValueError, TypeError)):

            class Builder(BagBuilderBase):
                @component()
                def mycomp(self, comp: Bag): ...  # Ellipsis body - not allowed


# =============================================================================
# Tests for kwargs validation on components
# =============================================================================


class TestComponentKwargsValidation:
    """Tests for kwargs validation on components."""

    def test_component_validates_typed_kwargs(self):
        """Component validates typed kwargs at call time (before expansion)."""
        from typing import Annotated

        from genro_builders.builders import Range

        class Builder(BagBuilderBase):
            @component(sub_tags="")
            def myform(
                self, comp: Bag, cols: Annotated[int, Range(ge=1, le=12)] = None, **kwargs
            ):
                return comp

        bag = Bag(builder=Builder)

        # Valid
        bag.myform(cols=6)

        # Invalid - should fail at call time, not compile time
        with pytest.raises(ValueError, match="must be >= 1"):
            bag.myform(cols=0)

        with pytest.raises(ValueError, match="must be <= 12"):
            bag.myform(cols=20)


# =============================================================================
# Tests for component node creation (structure, not expansion)
# =============================================================================


class TestComponentNodeCreation:
    """Tests for component node creation at call time."""

    def test_component_creates_node_with_tag(self):
        """Calling component creates node with correct tag."""

        class Builder(BagBuilderBase):
            @component(sub_tags="")
            def myform(self, comp: Bag, **kwargs):
                return comp

        bag = Bag(builder=Builder)
        bag.myform()

        node = bag.get_node("myform_0")
        assert node is not None
        assert node.tag == "myform"

    def test_component_attrs_stored_on_node(self):
        """Component attributes are stored on node at call time."""

        class Builder(BagBuilderBase):
            @component(sub_tags="")
            def myform(self, comp: Bag, **kwargs):
                return comp

        bag = Bag(builder=Builder)
        bag.myform(title="Form Title", css_class="my-form")

        node = bag.get_node("myform_0")
        assert node.attr.get("title") == "Form Title"
        assert node.attr.get("css_class") == "my-form"

    def test_component_and_elements_in_same_builder(self):
        """Builder can have both components and elements."""

        class Builder(BagBuilderBase):
            @component(sub_tags="")
            def form(self, comp: Bag, **kwargs):
                return comp

            @element()
            def div(self): ...

        bag = Bag(builder=Builder)
        bag.div()
        bag.form()
        bag.div()

        assert len(bag) == 3
        nodes = list(bag.nodes)
        assert nodes[0].tag == "div"
        assert nodes[1].tag == "form"
        assert nodes[2].tag == "div"

    def test_component_inside_element(self):
        """Component can be placed inside an element."""

        class Builder(BagBuilderBase):
            @element(sub_tags="form")
            def div(self): ...

            @component(sub_tags="")
            def form(self, comp: Bag, **kwargs):
                return comp

        bag = Bag(builder=Builder)
        div = bag.div()
        div.form()

        assert len(div.value) == 1
        form_node = div.value.get_node("form_0")
        assert form_node.tag == "form"

    def test_component_node_label_generation(self):
        """Component nodes get auto-generated labels like elements."""

        class Builder(BagBuilderBase):
            @component(sub_tags="")
            def myform(self, comp: Bag, **kwargs):
                return comp

        bag = Bag(builder=Builder)
        bag.myform()
        bag.myform()
        bag.myform()

        labels = list(bag.keys())
        assert labels == ["myform_0", "myform_1", "myform_2"]

    def test_component_custom_label(self):
        """Component can have custom node_label."""

        class Builder(BagBuilderBase):
            @component(sub_tags="")
            def myform(self, comp: Bag, **kwargs):
                return comp

        bag = Bag(builder=Builder)
        bag.myform(node_label="my_custom_form")

        assert bag.get_node("my_custom_form") is not None
        assert bag.get_node("my_custom_form").tag == "myform"


# =============================================================================
# Tests for builder override - STRUCTURE only
# =============================================================================


class TestComponentBuilderOverrideStructure:
    """Tests for builder override in schema structure."""

    def test_builder_override_stored_in_schema(self):
        """builder= parameter is stored in schema as component_builder."""

        class InnerBuilder(BagBuilderBase):
            @element()
            def special(self): ...

        class OuterBuilder(BagBuilderBase):
            @component(builder=InnerBuilder)
            def with_inner(self, comp: Bag, **kwargs):
                return comp

        node = OuterBuilder._class_schema.get_node("with_inner")
        # Stored as component_builder, not builder
        assert node.attr.get("component_builder") is InnerBuilder

    def test_override_builder_stored_in_resolver(self):
        """Component with builder override stores it in the resolver."""

        class InnerBuilder(BagBuilderBase):
            @element()
            def special(self): ...

        class OuterBuilder(BagBuilderBase):
            @component(builder=InnerBuilder)
            def with_inner(self, comp: Bag, **kwargs):
                return comp

        bag = Bag(builder=OuterBuilder)
        bag.with_inner()

        # Resolver has the override builder class
        node = bag.get_node("with_inner_0")
        assert node.resolver is not None
        assert node.resolver._kw["builder_class"] is InnerBuilder
