# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for dispatch, element creation, sub_tags/parent_tags validation,
lazy bag creation, and grammar priority on source bags."""

import warnings

import pytest

from genro_builders import BagBuilderBase
from genro_builders.builder_bag import BuilderBag as Bag
from genro_builders.builder import element


# =============================================================================
# Tests for BagBuilderBase functionality
# =============================================================================


class TestBagBuilderBase:
    """Tests for BagBuilderBase functionality."""

    def test_bag_with_builder(self):
        """Bag can be created with a builder class."""

        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        assert isinstance(bag.builder, Builder)

    def test_bag_without_builder(self):
        """Bag without builder works normally."""
        bag = Bag()
        assert bag.builder is None
        bag["test"] = "value"
        assert bag["test"] == "value"

    def test_builder_creates_node_with_tag(self):
        """Builder creates nodes with correct tag."""

        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        node = bag.item(name="test")

        assert node.node_tag == "item"
        assert node.label == "item_0"
        assert node.attr.get("name") == "test"

    def test_builder_auto_label_generation(self):
        """Builder auto-generates unique labels."""

        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        bag.item()
        bag.item()
        bag.item()

        labels = list(bag.keys())
        assert labels == ["item_0", "item_1", "item_2"]

    def test_builder_element_accepts_kwargs(self):
        """Builder element accepts kwargs as attributes."""

        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        node = bag.item(custom="injected")

        assert node.attr.get("custom") == "injected"

    def test_builder_default_handler_used(self):
        """Builder uses default handler for ellipsis methods."""

        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        node = bag.item(name="test")

        # Default handler should work
        assert node.node_tag == "item"
        assert node.attr.get("name") == "test"


# =============================================================================
# Tests for lazy Bag creation
# =============================================================================


class TestLazyBagCreation:
    """Tests for lazy Bag creation on branch nodes."""

    def test_branch_node_starts_with_none_value(self):
        """Branch node starts with value=None (lazy)."""

        class Builder(BagBuilderBase):
            @element(sub_tags="item")
            def container(self): ...

            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        container = bag.container()

        assert container.value is None

    def test_bag_created_on_first_child(self):
        """Bag created lazily when first child is added."""

        class Builder(BagBuilderBase):
            @element(sub_tags="item")
            def container(self): ...

            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        container = bag.container()
        container.item()

        assert isinstance(container.value, Bag)
        assert container.value.builder is bag.builder


# =============================================================================
# Tests for sub_tags validation
# =============================================================================


class TestSubTagsValidation:
    """Tests for sub_tags validation."""

    def test_valid_child_allowed(self):
        """Valid child tag is allowed."""

        class Builder(BagBuilderBase):
            @element(sub_tags="span,p")
            def div(self): ...

            @element()
            def span(self): ...

            @element()
            def p(self): ...

        bag = Bag(builder=Builder)
        div = bag.div()
        div.span()  # Should not raise
        div.p()  # Should not raise

        assert len(div.value) == 2

    def test_invalid_child_rejected(self):
        """Invalid child tag is rejected."""

        class Builder(BagBuilderBase):
            @element(sub_tags="span")
            def div(self): ...

            @element()
            def span(self): ...

            @element()
            def img(self): ...

        bag = Bag(builder=Builder)
        div = bag.div()

        with pytest.raises(ValueError, match="not allowed"):
            div.img()

    def test_void_element_rejects_children(self):
        """Bug: sub_tags='' (void element) should reject ALL children.

        Empty string means "no children allowed", but was being treated
        as "no validation" because '' is falsy in Python.
        """

        class Builder(BagBuilderBase):
            @element(sub_tags="")  # void element - no children allowed
            def br(self): ...

            @element()
            def span(self): ...

        bag = Bag(builder=Builder)
        br = bag.br()

        # void element should reject any child
        with pytest.raises(ValueError, match="not allowed"):
            br.span()


# =============================================================================
# Tests for sub_tags="*" wildcard semantics
# =============================================================================


class TestSubTagsWildcard:
    """Tests for sub_tags="*" wildcard that accepts any children."""

    def test_wildcard_accepts_any_child(self):
        """sub_tags="*" allows any child tag."""

        class Builder(BagBuilderBase):
            @element(sub_tags="*")  # container accepts any children
            def container(self): ...

            @element(sub_tags="")  # leaf element
            def span(self): ...

            @element(sub_tags="")
            def div(self): ...

            @element(sub_tags="")
            def custom(self): ...

        bag = Bag(builder=Builder)
        container = bag.container()
        container.span()  # OK
        container.div()  # OK
        container.custom()  # OK

        assert len(container.value) == 3

    def test_wildcard_allows_multiple_same_children(self):
        """sub_tags="*" allows unlimited children of same type."""

        class Builder(BagBuilderBase):
            @element(sub_tags="*")
            def container(self): ...

            @element(sub_tags="")
            def item(self): ...

        bag = Bag(builder=Builder)
        container = bag.container()
        for _ in range(10):
            container.item()

        assert len(container.value) == 10

    def test_wildcard_with_nested_containers(self):
        """sub_tags="*" works with nested wildcard containers."""

        class Builder(BagBuilderBase):
            @element(sub_tags="*")
            def outer(self): ...

            @element(sub_tags="*")
            def inner(self): ...

            @element(sub_tags="")
            def leaf(self): ...

        bag = Bag(builder=Builder)
        outer = bag.outer()
        inner = outer.inner()
        inner.leaf()

        assert len(outer.value) == 1
        assert len(inner.value) == 1

    def test_wildcard_parse_returns_star(self):
        """_parse_sub_tags_spec returns '*' for wildcard."""
        from genro_builders.builder import _parse_sub_tags_spec

        result = _parse_sub_tags_spec("*")
        assert result == "*"

    def test_empty_string_is_leaf(self):
        """sub_tags='' is a leaf element (no children allowed)."""

        class Builder(BagBuilderBase):
            @element(sub_tags="")  # leaf
            def leaf(self): ...

            @element(sub_tags="")
            def child(self): ...

        bag = Bag(builder=Builder)
        leaf = bag.leaf()

        with pytest.raises(ValueError, match="not allowed"):
            leaf.child()

    def test_empty_string_parse_returns_empty_dict(self):
        """_parse_sub_tags_spec returns empty dict for ''."""
        from genro_builders.builder import _parse_sub_tags_spec

        result = _parse_sub_tags_spec("")
        assert result == {}

    def test_explicit_tags_still_validate(self):
        """Explicit sub_tags like 'foo,bar' still validate."""

        class Builder(BagBuilderBase):
            @element(sub_tags="allowed")
            def container(self): ...

            @element(sub_tags="")
            def allowed(self): ...

            @element(sub_tags="")
            def forbidden(self): ...

        bag = Bag(builder=Builder)
        container = bag.container()
        container.allowed()  # OK

        with pytest.raises(ValueError, match="not allowed"):
            container.forbidden()  # Not allowed

    def test_check_with_wildcard_container_valid(self):
        """check() returns empty for valid wildcard container."""

        class Builder(BagBuilderBase):
            @element(sub_tags="*")
            def container(self): ...

            @element(sub_tags="")
            def item(self): ...

        bag = Bag(builder=Builder)
        container = bag.container()
        container.item()
        container.item()

        result = bag.builder._check()
        assert result == []


# =============================================================================
# Tests for parent_tags validation
# =============================================================================


class TestParentTagsValidation:
    """Tests for parent_tags validation (child declares valid parents)."""

    def test_valid_parent_allowed(self):
        """Child with parent_tags can be placed in valid parent."""

        class Builder(BagBuilderBase):
            @element(sub_tags="li")
            def ul(self): ...

            @element(parent_tags="ul")
            def li(self): ...

        bag = Bag(builder=Builder)
        ul = bag.ul()
        ul.li()  # Should not raise

        assert len(ul.value) == 1

    def test_invalid_parent_rejected(self):
        """Child with parent_tags cannot be placed in invalid parent."""

        class Builder(BagBuilderBase):
            @element(sub_tags="li,span")
            def div(self): ...

            @element(sub_tags="li")
            def ul(self): ...

            @element(parent_tags="ul")  # li can only be in ul
            def li(self): ...

            @element()
            def span(self): ...

        bag = Bag(builder=Builder)
        div = bag.div()

        with pytest.raises(ValueError, match="parent_tags requires"):
            div.li()  # div is not a valid parent for li

    def test_parent_tags_at_root_rejected(self):
        """Child with parent_tags cannot be placed at root if root not in list."""

        class Builder(BagBuilderBase):
            @element(sub_tags="li")
            def ul(self): ...

            @element(parent_tags="ul")  # li can only be in ul
            def li(self): ...

        bag = Bag(builder=Builder)

        with pytest.raises(ValueError, match="parent_tags requires"):
            bag.li()  # root is not a valid parent for li

    def test_parent_tags_multiple_valid_parents(self):
        """Child with multiple parent_tags can be placed in any of them."""

        class Builder(BagBuilderBase):
            @element(sub_tags="li")
            def ul(self): ...

            @element(sub_tags="li")
            def ol(self): ...

            @element(parent_tags="ul, ol")  # li can be in ul or ol
            def li(self): ...

        bag = Bag(builder=Builder)
        ul = bag.ul()
        ul.li()  # ul is valid

        ol = bag.ol()
        ol.li()  # ol is valid

        assert len(ul.value) == 1
        assert len(ol.value) == 1

    def test_no_parent_tags_allows_anywhere(self):
        """Element without parent_tags can be placed anywhere."""

        class Builder(BagBuilderBase):
            @element(sub_tags="span")
            def div(self): ...

            @element()  # no parent_tags - can be placed anywhere
            def span(self): ...

        bag = Bag(builder=Builder)
        bag.span()  # at root - OK
        div = bag.div()
        div.span()  # in div - OK

        assert len(bag) == 2


# =============================================================================
# Tests for grammar priority on source bags (Fase -1)
# =============================================================================


class TestGrammarPriority:
    """Grammar tags have priority over Bag methods on source bags."""

    def test_colliding_tag_creates_element(self):
        """source.keys() creates a grammar tag, not Bag.keys()."""

        class Builder(BagBuilderBase):
            @element()
            def keys(self): ...

        b = Builder()
        b.source.keys(node_value="test")
        assert b.source.get_node("keys_0") is not None

    def test_bag_method_via_prefix(self):
        """source.bag_keys() calls Bag.keys()."""

        class Builder(BagBuilderBase):
            @element()
            def keys(self): ...

        b = Builder()
        b.source.keys(node_value="v1")
        result = b.source.bag_keys()
        assert isinstance(result, list)

    def test_no_collision_tag_works_normally(self):
        """Tags without collision work as before."""

        class Builder(BagBuilderBase):
            @element()
            def mytag(self): ...

        b = Builder()
        b.source.mytag(node_value="hello")
        assert b.source.get_node("mytag_0") is not None

    def test_bag_method_without_collision(self):
        """Bag methods without collision work normally (no prefix needed)."""

        class Builder(BagBuilderBase):
            @element()
            def mytag(self): ...

        b = Builder()
        b.source.mytag(node_value="v")
        result = b.source.get_item("mytag_0")
        assert result is not None

    def test_bag_prefix_works_without_collision(self):
        """bag_ prefix works even when there's no collision."""

        class Builder(BagBuilderBase):
            @element()
            def mytag(self): ...

        b = Builder()
        b.source.mytag(node_value="v")
        result = b.source.bag_get_item("mytag_0")
        assert result is not None

    def test_no_rename_warning(self):
        """No rename warning is emitted (el_ convention eliminated)."""

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")

            class Builder(BagBuilderBase):
                @element()
                def keys(self): ...

            rename_warnings = [x for x in w if "renamed" in str(x.message).lower()]
            assert len(rename_warnings) == 0

    def test_schema_keeps_original_name(self):
        """Schema stores the original tag name, not el_ prefixed."""

        class Builder(BagBuilderBase):
            @element()
            def keys(self): ...

        assert Builder._class_schema.get_node("keys") is not None
        assert Builder._class_schema.get_node("el_keys") is None

    def test_no_builder_delegation(self):
        """Source bag does NOT delegate to builder for non-schema names."""

        class Builder(BagBuilderBase):
            @element()
            def mytag(self): ...

        b = Builder()
        with pytest.raises(AttributeError):
            b.source.render  # noqa: B018


# =============================================================================
# Tests for parent_tags inside component handlers (Issue #18)
# =============================================================================


class TestComponentParentTagsFix:
    """Component handler bodies skip parent_tags validation (Issue #18)."""

    def test_component_with_parent_tags_elements(self):
        """Elements with parent_tags can be created inside component handler."""
        from genro_builders.builder import component

        class Builder(BagBuilderBase):
            @element(sub_tags="paragraph,address_block")
            def document(self): ...

            @element(parent_tags="document,address_block")
            def paragraph(self): ...

            @component(sub_tags="", parent_tags="document")
            def address_block(self, comp, **kwargs):
                comp.paragraph()
                comp.paragraph()

        b = Builder()
        doc = b.source.document()
        doc.address_block()

        # Build should not raise — paragraph inside component skips parent_tags
        b.build()
        assert b.built is not None

    def test_component_parent_tags_validated_on_component_itself(self):
        """The component itself still validates parent_tags at creation."""
        from genro_builders.builder import component

        class Builder(BagBuilderBase):
            @element(sub_tags="paragraph,address_block")
            def document(self): ...

            @element()
            def paragraph(self): ...

            @component(sub_tags="", parent_tags="document")
            def address_block(self, comp, **kwargs):
                comp.paragraph()

        b = Builder()
        # address_block at root should fail — parent_tags="document"
        with pytest.raises(ValueError, match="parent_tags requires"):
            b.source.address_block()

    def test_component_elements_in_built_under_correct_parent(self):
        """After build, component inner elements are under the correct parent."""
        from genro_builders.builder import component

        class Builder(BagBuilderBase):
            @element(sub_tags="paragraph,block")
            def document(self): ...

            @element(parent_tags="document,block")
            def paragraph(self): ...

            @component(sub_tags="", parent_tags="document")
            def block(self, comp, **kwargs):
                comp.paragraph()

        b = Builder()
        doc = b.source.document()
        doc.block()
        b.build()

        # The block node in built is under document_0
        doc_bag = b.built.get_item("document_0")
        assert doc_bag is not None
        block_node = doc_bag.get_node("block_0")
        assert block_node is not None
        assert block_node.value is not None
        para = block_node.value.get_node("paragraph_0")
        assert para is not None
        assert para.node_tag == "paragraph"
