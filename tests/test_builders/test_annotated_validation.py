# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for Annotated type validation, node_value validation,
and _get_call_args_validations lookup."""

from decimal import Decimal
from typing import Literal

import pytest

from genro_builders import BagBuilderBase
from genro_builders.builder import SchemaBuilder
from genro_builders.builder_bag import BuilderBag as Bag
from genro_builders.builders import Range, Regex, element


# =============================================================================
# Tests for attribute validation via Annotated
# =============================================================================


class TestAnnotatedValidation:
    """Tests for attribute validation via call_args_validations in schema.

    With the new architecture, @element has empty body and validation is
    defined via call_args_validations parameter or SchemaBuilder.
    """

    def test_range_valid_via_schema(self):
        """Range constraint via SchemaBuilder accepts valid value."""
        schema = Bag(builder=SchemaBuilder)
        schema.builder.item(
            "td",
            call_args_validations={
                "colspan": (int, [Range(ge=1, le=10)], None),
            },
        )

        class Builder(BagBuilderBase):
            schema_path = None  # Will be set below

        Builder._class_schema = schema
        bag = Bag(builder=Builder)
        bag.td(colspan=5)  # Should not raise

    def test_range_min_invalid_via_schema(self):
        """Range constraint via SchemaBuilder rejects value below minimum."""
        schema = Bag(builder=SchemaBuilder)
        schema.builder.item(
            "td",
            call_args_validations={
                "colspan": (int, [Range(ge=1, le=10)], None),
            },
        )

        class Builder(BagBuilderBase):
            schema_path = None

        Builder._class_schema = schema
        bag = Bag(builder=Builder)
        with pytest.raises(ValueError, match="must be >= 1"):
            bag.td(colspan=0)

    def test_range_max_invalid_via_schema(self):
        """Range constraint via SchemaBuilder rejects value above maximum."""
        schema = Bag(builder=SchemaBuilder)
        schema.builder.item(
            "td",
            call_args_validations={
                "colspan": (int, [Range(ge=1, le=10)], None),
            },
        )

        class Builder(BagBuilderBase):
            schema_path = None

        Builder._class_schema = schema
        bag = Bag(builder=Builder)
        with pytest.raises(ValueError, match="must be <= 10"):
            bag.td(colspan=20)

    def test_literal_valid_via_schema(self):
        """Literal constraint via SchemaBuilder accepts valid value."""
        schema = Bag(builder=SchemaBuilder)
        schema.builder.item(
            "td",
            call_args_validations={
                "scope": (Literal["row", "col"], [], None),
            },
        )

        class Builder(BagBuilderBase):
            schema_path = None

        Builder._class_schema = schema
        bag = Bag(builder=Builder)
        bag.td(scope="row")  # Should not raise

    def test_literal_invalid_via_schema(self):
        """Literal constraint via SchemaBuilder rejects invalid value."""
        schema = Bag(builder=SchemaBuilder)
        schema.builder.item(
            "td",
            call_args_validations={
                "scope": (Literal["row", "col"], [], None),
            },
        )

        class Builder(BagBuilderBase):
            schema_path = None

        Builder._class_schema = schema
        bag = Bag(builder=Builder)
        with pytest.raises(ValueError, match="expected"):
            bag.td(scope="invalid")

    def test_regex_valid_via_schema(self):
        """Regex constraint via SchemaBuilder accepts matching value."""
        schema = Bag(builder=SchemaBuilder)
        schema.builder.item(
            "email",
            call_args_validations={
                "address": (str, [Regex(r"^[\w\.-]+@[\w\.-]+\.\w+$")], None),
            },
        )

        class Builder(BagBuilderBase):
            schema_path = None

        Builder._class_schema = schema
        bag = Bag(builder=Builder)
        bag.email(address="test@example.com")  # Should not raise

    def test_regex_invalid_via_schema(self):
        """Regex constraint via SchemaBuilder rejects non-matching value."""
        schema = Bag(builder=SchemaBuilder)
        schema.builder.item(
            "email",
            call_args_validations={
                "address": (str, [Regex(r"^[\w\.-]+@[\w\.-]+\.\w+$")], None),
            },
        )

        class Builder(BagBuilderBase):
            schema_path = None

        Builder._class_schema = schema
        bag = Bag(builder=Builder)
        with pytest.raises(ValueError, match="must match pattern"):
            bag.email(address="not-an-email")

    def test_decimal_range_via_schema(self):
        """Decimal type with Range constraints via SchemaBuilder."""
        schema = Bag(builder=SchemaBuilder)
        schema.builder.item(
            "payment",
            call_args_validations={
                "amount": (Decimal, [Range(ge=0, le=1000)], None),
            },
        )

        class Builder(BagBuilderBase):
            schema_path = None

        Builder._class_schema = schema
        bag = Bag(builder=Builder)
        bag.payment(amount=Decimal("500.50"))  # Should not raise

        with pytest.raises(ValueError, match="must be >= 0"):
            bag.payment(amount=Decimal("-1"))

        with pytest.raises(ValueError, match="must be <= 1000"):
            bag.payment(amount=Decimal("1001"))


# =============================================================================
# Tests for node_value validation (node content vs attributes)
# =============================================================================


class TestValueValidation:
    """Tests for node_value validation for node content."""

    def test_value_positional_basic(self):
        """node_value passed positionally becomes node.value."""

        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        node = bag.item("contenuto")
        assert node.value == "contenuto"

    def test_value_keyword_basic(self):
        """node_value can also be passed as keyword."""

        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        node = bag.item(node_value="contenuto")
        assert node.value == "contenuto"

    def test_value_and_attr_disambiguation(self):
        """node_value (content) and arbitrary attr are separate."""

        class Builder(BagBuilderBase):
            @element()
            def input(self): ...

        bag = Bag(builder=Builder)
        node = bag.input("node content", default="attr value")
        assert node.value == "node content"
        assert node.attr["default"] == "attr value"

    def test_value_validation_type_via_schema(self):
        """node_value type is validated via schema."""
        schema = Bag(builder=SchemaBuilder)
        schema.builder.item(
            "number",
            call_args_validations={
                "node_value": (int, [], None),
            },
        )

        class Builder(BagBuilderBase):
            schema_path = None

        Builder._class_schema = schema
        bag = Bag(builder=Builder)
        node = bag.number(42)
        assert node.value == 42

        with pytest.raises(ValueError, match=r"expected.*int"):
            bag.number("not a number")

    def test_value_validation_annotated_range_via_schema(self):
        """node_value with Annotated Range validator via schema."""
        schema = Bag(builder=SchemaBuilder)
        schema.builder.item(
            "amount",
            call_args_validations={
                "node_value": (Decimal, [Range(ge=0)], None),
            },
        )

        class Builder(BagBuilderBase):
            schema_path = None

        Builder._class_schema = schema
        bag = Bag(builder=Builder)
        node = bag.amount(Decimal("10"))
        assert node.value == Decimal("10")

        with pytest.raises(ValueError, match="must be >= 0"):
            bag.amount(Decimal("-5"))

    def test_value_validation_annotated_regex_via_schema(self):
        """node_value with Annotated Regex validator via schema."""
        schema = Bag(builder=SchemaBuilder)
        schema.builder.item(
            "code",
            call_args_validations={
                "node_value": (str, [Regex(r"^[A-Z]{3}$")], None),
            },
        )

        class Builder(BagBuilderBase):
            schema_path = None

        Builder._class_schema = schema
        bag = Bag(builder=Builder)
        node = bag.code("ABC")
        assert node.value == "ABC"

        with pytest.raises(ValueError, match="must match pattern"):
            bag.code("abc")

    def test_value_default_element_positional(self):
        """Default element handler accepts node_value positionally."""

        class Builder(BagBuilderBase):
            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        node = bag.item("my value")
        assert node.value == "my value"

    def test_attr_validated_when_typed_via_schema(self):
        """Typed attributes are validated via schema."""
        schema = Bag(builder=SchemaBuilder)
        schema.builder.item(
            "input",
            call_args_validations={
                "default": (str, [], None),
            },
        )

        class Builder(BagBuilderBase):
            schema_path = None

        Builder._class_schema = schema
        bag = Bag(builder=Builder)
        node = bag.input(default="text")
        assert node.attr["default"] == "text"

        with pytest.raises(ValueError, match=r"expected.*str"):
            bag.input(default=123)

