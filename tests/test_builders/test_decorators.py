# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for decorator syntax, schema registration, meta, and mixin inheritance."""

import pytest

from genro_builders import BagBuilderBase
from genro_builders.builder_bag import BuilderBag as Bag
from genro_builders.builder import abstract, component, element


# =============================================================================
# Tests for @element decorator - handler detection
# =============================================================================


class TestElementDecoratorHandlerDetection:
    """Tests for @element decorator handler detection."""

    def test_ellipsis_body_sets_adapter_name_none(self):
        """@element with ... body sets adapter_name=None in schema."""

        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        # Schema should have adapter_name=None
        node = Builder._class_schema.get_node("item")
        assert node is not None
        assert node.attr.get("adapter_name") is None

    def test_real_body_raises_value_error(self):
        """@element with real body raises ValueError (must use @component)."""
        with pytest.raises(ValueError, match="must have empty body"):

            class Builder(BagBuilderBase):
                @element()
                def item(self, **attr):
                    attr.setdefault("custom", "value")
                    return attr

    def test_ellipsis_method_removed_from_class(self):
        """@element with ... body removes method from class."""

        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        # Method should be removed (no _el_item either)
        assert not hasattr(Builder, "item")
        assert not hasattr(Builder, "_el_item")

    def test_ellipsis_inline_with_params(self):
        """@element with inline ... and parameters sets adapter_name=None."""

        class Builder(BagBuilderBase):
            @element()
            def alfa(self, aa=None): ...

        node = Builder._class_schema.get_node("alfa")
        assert node is not None
        assert node.attr.get("adapter_name") is None

    def test_ellipsis_newline_with_params(self):
        """@element with ... on separate line sets adapter_name=None."""

        class Builder(BagBuilderBase):
            @element()
            def alfa(self, aa=None): ...

        node = Builder._class_schema.get_node("alfa")
        assert node is not None
        assert node.attr.get("adapter_name") is None

    def test_ellipsis_with_docstring_and_params(self):
        """@element with docstring and ... sets adapter_name=None."""

        class Builder(BagBuilderBase):
            @element()
            def alfa(self, aa=None):
                "this is my method"
                ...

        node = Builder._class_schema.get_node("alfa")
        assert node is not None
        assert node.attr.get("adapter_name") is None


# =============================================================================
# Tests for @abstract decorator
# =============================================================================


class TestAbstractDecorator:
    """Tests for @abstract decorator."""

    def test_abstract_creates_at_prefixed_entry(self):
        """@abstract creates @name entry in schema."""

        class Builder(BagBuilderBase):
            @abstract(sub_tags="span,p")
            def flow(self): ...

        # Schema should have @flow
        node = Builder._class_schema.get_node("@flow")
        assert node is not None
        assert node.attr.get("sub_tags") == "span,p"

    def test_abstract_method_removed_from_class(self):
        """@abstract removes method from class."""

        class Builder(BagBuilderBase):
            @abstract(sub_tags="span,p")
            def flow(self): ...

        assert not hasattr(Builder, "flow")
        assert not hasattr(Builder, "_el_flow")

    def test_iteration_returns_all_nodes(self):
        """Iteration returns all schema nodes including abstracts."""

        class Builder(BagBuilderBase):
            @abstract(sub_tags="span,p")
            def flow(self): ...

            @element()
            def div(self): ...

            @element()
            def span(self): ...

        bag = Bag(builder=Builder)
        labels = [node.label for node in bag.builder]
        assert "div" in labels
        assert "span" in labels
        assert "@flow" in labels

    def test_abstract_not_in_contains(self):
        """Abstract elements work with 'in' operator."""

        class Builder(BagBuilderBase):
            @abstract(sub_tags="span,p")
            def flow(self): ...

            @element()
            def div(self): ...

        bag = Bag(builder=Builder)
        assert "div" in bag.builder
        assert "@flow" in bag.builder  # Abstracts are in schema


# =============================================================================
# Tests for inherits_from
# =============================================================================


class TestInheritsFrom:
    """Tests for inherits_from inheritance resolution."""

    def test_element_inherits_sub_tags_from_abstract(self):
        """Element inherits sub_tags from abstract via inherits_from."""

        class Builder(BagBuilderBase):
            @abstract(sub_tags="span,p,a")
            def phrasing(self): ...

            @element(inherits_from="@phrasing")
            def div(self): ...

            @element()
            def span(self): ...

            @element()
            def p(self): ...

            @element()
            def a(self): ...

        bag = Bag(builder=Builder)
        info = bag.builder._get_schema_info("div")
        assert info.get("sub_tags") == "span,p,a"

    def test_element_can_override_inherited_attrs(self):
        """Element attrs override inherited attrs from abstract."""

        class Builder(BagBuilderBase):
            @abstract(sub_tags="a,b,c")
            def base(self): ...

            @element(inherits_from="@base", sub_tags="x,y,z")
            def custom(self): ...

            @element()
            def x(self): ...

            @element()
            def y(self): ...

            @element()
            def z(self): ...

        bag = Bag(builder=Builder)
        info = bag.builder._get_schema_info("custom")
        # sub_tags overridden
        assert info.get("sub_tags") == "x,y,z"

    def test_multiple_inheritance_comma_separated(self):
        """Element can inherit from multiple abstracts via comma-separated list."""

        class Builder(BagBuilderBase):
            @abstract(sub_tags="a,b")
            def base_tags(self): ...

            @abstract(parent_tags="container")
            def base_parent(self): ...

            @element(inherits_from="@base_tags,@base_parent")
            def multi(self): ...

            @element()
            def a(self): ...

            @element()
            def b(self): ...

            @element(sub_tags="multi")
            def container(self): ...

        bag = Bag(builder=Builder)
        info = bag.builder._get_schema_info("multi")
        # Inherits from both abstracts
        assert info.get("sub_tags") == "a,b"
        assert info.get("parent_tags") == "container"

    def test_multiple_inheritance_first_wins(self):
        """In multiple inheritance, first parent wins (closest to element)."""

        class Builder(BagBuilderBase):
            @abstract(sub_tags="a,b", parent_tags="first")
            def first(self): ...

            @abstract(sub_tags="x,y", parent_tags="second")
            def second(self): ...

            @element(inherits_from="@first,@second")
            def derived(self): ...

            @element()
            def a(self): ...

            @element()
            def b(self): ...

        bag = Bag(builder=Builder)
        info = bag.builder._get_schema_info("derived")
        # @first wins over @second (first is closest)
        assert info.get("sub_tags") == "a,b"
        assert info.get("parent_tags") == "first"


# =============================================================================
# Tests for @element decorator - tags parameter
# =============================================================================


class TestElementDecoratorTags:
    """Tests for @element decorator tags parameter."""

    def test_no_tags_uses_method_name(self):
        """@element with no tags uses method name as tag."""

        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        assert Builder._class_schema.get_node("item") is not None

    def test_single_tag_string_adds_to_method_name(self):
        """@element with tags adds them to method name."""

        class Builder(BagBuilderBase):
            @element(tags="product")
            def item(self): ...

        # Both method name and tags are registered
        assert Builder._class_schema.get_node("item") is not None
        assert Builder._class_schema.get_node("product") is not None

    def test_underscore_method_excludes_name(self):
        """@element on _method excludes method name from tags."""

        class Builder(BagBuilderBase):
            @element(tags="product")
            def _item(self): ...

        # Only tags are registered, not _item
        assert Builder._class_schema.get_node("product") is not None
        assert Builder._class_schema.get_node("_item") is None

    def test_multiple_tags_string(self):
        """@element with comma-separated tags string."""

        class Builder(BagBuilderBase):
            @element(tags="apple, banana, cherry")
            def _fruit(self): ...

        assert Builder._class_schema.get_node("apple") is not None
        assert Builder._class_schema.get_node("banana") is not None
        assert Builder._class_schema.get_node("cherry") is not None
        assert Builder._class_schema.get_node("_fruit") is None

    def test_multiple_tags_tuple(self):
        """@element with tuple of tags."""

        class Builder(BagBuilderBase):
            @element(tags=("red", "green", "blue"))
            def _color(self): ...

        assert Builder._class_schema.get_node("red") is not None
        assert Builder._class_schema.get_node("green") is not None
        assert Builder._class_schema.get_node("blue") is not None


# =============================================================================
# Tests for _meta
# =============================================================================


class TestMeta:
    """Tests for _meta in @element and @abstract decorators."""

    def test_element_meta_dict(self):
        """@element with _meta dict stores in schema."""

        class Builder(BagBuilderBase):
            @element(_meta={"compile_module": "textual.containers", "compile_class": "Vertical"})
            def vertical(self): ...

        info = Builder._class_schema.get_attr("vertical")
        assert info["_meta"] == {"compile_module": "textual.containers", "compile_class": "Vertical"}

    def test_abstract_meta(self):
        """@abstract with _meta stores in schema."""

        class Builder(BagBuilderBase):
            @abstract(sub_tags="child", _meta={"compile_module": "textual.containers"})
            def base_container(self): ...

        info = Builder._class_schema.get_attr("@base_container")
        assert info["_meta"] == {"compile_module": "textual.containers"}

    def test_inherits_meta_merge(self):
        """Element inherits and merges _meta from abstract."""

        class Builder(BagBuilderBase):
            @abstract(sub_tags="child", _meta={"compile_module": "textual.containers"})
            def base_container(self): ...

            @element(inherits_from="@base_container", _meta={"compile_class": "Vertical"})
            def vertical(self): ...

        bag = Bag(builder=Builder)
        info = bag.builder._get_schema_info("vertical")

        assert info["_meta"] == {"compile_module": "textual.containers", "compile_class": "Vertical"}

    def test_inherits_meta_override(self):
        """Element can override inherited _meta values."""

        class Builder(BagBuilderBase):
            @abstract(
                sub_tags="child",
                _meta={"compile_module": "textual.containers", "compile_class": "Container"},
            )
            def base_container(self): ...

            @element(inherits_from="@base_container", _meta={"compile_class": "Vertical"})
            def vertical(self): ...

        bag = Bag(builder=Builder)
        info = bag.builder._get_schema_info("vertical")

        assert info["_meta"]["compile_module"] == "textual.containers"
        assert info["_meta"]["compile_class"] == "Vertical"

    def test_element_without_meta(self):
        """Element without _meta has no _meta in schema."""

        class Builder(BagBuilderBase):
            @element()
            def simple(self): ...

        info = Builder._class_schema.get_attr("simple")
        assert "_meta" not in info or info.get("_meta") is None

    def test_meta_with_mixed_keys(self):
        """_meta can contain any keys for any output."""

        class Builder(BagBuilderBase):
            @element(_meta={
                "compile_class": "Container",
                "renderer_svg_style": "rounded",
                "pdf_page_break": True,
            })
            def section(self): ...

        info = Builder._class_schema.get_attr("section")
        assert info["_meta"]["compile_class"] == "Container"
        assert info["_meta"]["renderer_svg_style"] == "rounded"
        assert info["_meta"]["pdf_page_break"] is True


# =============================================================================
# Tests for mixin class @element inheritance (Issue #6)
# =============================================================================


class TestMixinInheritance:
    """Tests for @element/@abstract/@component discovery from mixin classes."""

    def test_mixin_element_discovered(self):
        """@element on a mixin class is discovered by the composed builder."""

        class ItemMixin:
            @element(sub_tags="a,b")
            def item(self): ...

        class Builder(ItemMixin, BagBuilderBase):
            @element()
            def container(self): ...

        assert Builder._class_schema.get_node("item") is not None
        assert Builder._class_schema.get_node("container") is not None
        info = Builder._class_schema.get_attr("item")
        assert info.get("sub_tags") == "a,b"

    def test_mixin_abstract_discovered(self):
        """@abstract on a mixin class is discovered with @ prefix."""

        class AbstractMixin:
            @abstract(sub_tags="x,y")
            def base_tags(self): ...

        class Builder(AbstractMixin, BagBuilderBase):
            @element(inherits_from="@base_tags")
            def item(self): ...

        assert Builder._class_schema.get_node("@base_tags") is not None

    def test_mixin_component_discovered(self):
        """@component on a mixin class is discovered by the composed builder."""

        class CompMixin:
            @component()
            def panel(self, comp, **kwargs):
                return comp

        class Builder(CompMixin, BagBuilderBase):
            @element()
            def item(self): ...

        node = Builder._class_schema.get_node("panel")
        assert node is not None
        assert node.attr.get("is_component") is True
        assert node.attr.get("handler_name") == "_comp_panel"

    def test_mixin_override_priority(self):
        """Method defined on the class overrides the mixin version."""

        class ItemMixin:
            @element(sub_tags="from_mixin")
            def item(self): ...

        class Builder(ItemMixin, BagBuilderBase):
            @element(sub_tags="from_class")
            def item(self): ...

        info = Builder._class_schema.get_attr("item")
        assert info.get("sub_tags") == "from_class"

    def test_multiple_mixins(self):
        """Multiple mixins each contribute their @element methods."""

        class ServiceMixin:
            @element()
            def service(self): ...

        class NetworkMixin:
            @element()
            def network(self): ...

        class VolumeMixin:
            @element()
            def volume(self): ...

        class Builder(ServiceMixin, NetworkMixin, VolumeMixin, BagBuilderBase):
            @element()
            def container(self): ...

        for tag in ("service", "network", "volume", "container"):
            assert Builder._class_schema.get_node(tag) is not None

    def test_builder_inherits_parent_schema(self):
        """Child builder inherits parent's schema elements."""

        class BaseBuilder(BagBuilderBase):
            @element()
            def base_item(self): ...

        class ChildBuilder(BaseBuilder):
            @element()
            def child_item(self): ...

        # child_item is defined directly on ChildBuilder
        assert ChildBuilder._class_schema.get_node("child_item") is not None
        # base_item is inherited from BaseBuilder's schema
        assert ChildBuilder._class_schema.get_node("base_item") is not None
        # BaseBuilder still has only its own element
        assert BaseBuilder._class_schema.get_node("base_item") is not None
        assert BaseBuilder._class_schema.get_node("child_item") is None

    def test_mixin_reusable_across_builders(self):
        """A mixin can be used by multiple builders without interference."""

        class SharedMixin:
            @element(sub_tags="shared")
            def shared_item(self): ...

        class BuilderA(SharedMixin, BagBuilderBase):
            @element()
            def item_a(self): ...

        class BuilderB(SharedMixin, BagBuilderBase):
            @element()
            def item_b(self): ...

        assert BuilderA._class_schema.get_node("shared_item") is not None
        assert BuilderA._class_schema.get_node("item_a") is not None
        assert BuilderB._class_schema.get_node("shared_item") is not None
        assert BuilderB._class_schema.get_node("item_b") is not None
