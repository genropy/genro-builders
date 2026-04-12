# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for internal utility functions: validators, _check_type,
_split_annotated, _parse_sub_tags_spec, and _pop_decorated_methods."""

from typing import Annotated, Any, Literal

import pytest

from genro_builders import BagBuilderBase
from genro_builders.builder import Range, Regex, element


# =============================================================================
# Tests for Range and Regex validators
# =============================================================================


class TestValidatorClasses:
    """Tests for Range and Regex validator classes."""

    def test_regex_non_string_raises_type_error(self):
        """Regex validator raises TypeError for non-string value."""
        validator = Regex(pattern=r"\d+")

        with pytest.raises(TypeError, match="requires a str"):
            validator(123)  # Not a string

    def test_range_non_numeric_raises_type_error(self):
        """Range validator raises TypeError for non-numeric value."""
        validator = Range(ge=0, le=10)

        with pytest.raises(TypeError, match="requires int, float or Decimal"):
            validator("not a number")

    def test_range_gt_constraint(self):
        """Range validator with gt (greater than) constraint."""
        validator = Range(gt=5)

        validator(6)  # OK
        validator(100)  # OK

        with pytest.raises(ValueError, match="must be > 5"):
            validator(5)  # Equal to gt, should fail

    def test_range_lt_constraint(self):
        """Range validator with lt (less than) constraint."""
        validator = Range(lt=10)

        validator(9)  # OK
        validator(0)  # OK

        with pytest.raises(ValueError, match="must be < 10"):
            validator(10)  # Equal to lt, should fail


# =============================================================================
# Tests for _check_type function
# =============================================================================


class TestCheckTypeFunction:
    """Tests for _check_type internal function."""

    def test_literal_type_checking(self):
        """_check_type works with Literal type."""
        from genro_builders.builder import _check_type

        assert _check_type("a", Literal["a", "b", "c"]) is True
        assert _check_type("d", Literal["a", "b", "c"]) is False

    def test_list_type_checking(self):
        """_check_type works with list[T] type."""
        from genro_builders.builder import _check_type

        assert _check_type([1, 2, 3], list[int]) is True
        assert _check_type(["a", "b"], list[str]) is True
        assert _check_type([1, "mixed"], list[int]) is False
        assert _check_type("not a list", list[int]) is False
        # Empty list is valid
        assert _check_type([], list[int]) is True

    def test_dict_type_checking(self):
        """_check_type works with dict[K, V] type."""
        from genro_builders.builder import _check_type

        assert _check_type({"a": 1, "b": 2}, dict[str, int]) is True
        assert _check_type({1: "a", 2: "b"}, dict[int, str]) is True
        assert _check_type({"a": "b"}, dict[str, int]) is False
        assert _check_type("not a dict", dict[str, int]) is False
        # Empty dict is valid
        assert _check_type({}, dict[str, int]) is True

    def test_tuple_type_checking(self):
        """_check_type works with tuple[T, ...] type."""
        from genro_builders.builder import _check_type

        # Fixed-length tuple
        assert _check_type((1, "a"), tuple[int, str]) is True
        assert _check_type((1, 2), tuple[int, str]) is False
        assert _check_type("not a tuple", tuple[int, str]) is False

        # Variable-length tuple with ellipsis
        assert _check_type((1, 2, 3), tuple[int, ...]) is True
        assert _check_type((1, "mixed"), tuple[int, ...]) is False

    def test_set_type_checking(self):
        """_check_type works with set[T] type."""
        from genro_builders.builder import _check_type

        assert _check_type({1, 2, 3}, set[int]) is True
        assert _check_type({"a", "b"}, set[str]) is True
        assert _check_type({1, "mixed"}, set[int]) is False
        assert _check_type("not a set", set[int]) is False
        # Empty set is valid
        assert _check_type(set(), set[int]) is True

    def test_union_type_checking(self):
        """_check_type works with Union and | types."""
        from genro_builders.builder import _check_type

        # Using | syntax (Python 3.10+)
        assert _check_type(1, int | str) is True
        assert _check_type("hello", int | str) is True
        assert _check_type(1.5, int | str) is False

    def test_any_type_accepts_everything(self):
        """_check_type with Any accepts everything."""
        from genro_builders.builder import _check_type

        assert _check_type(1, Any) is True
        assert _check_type("string", Any) is True
        assert _check_type(None, Any) is True
        assert _check_type([1, 2, 3], Any) is True

    def test_none_type_checking(self):
        """_check_type with NoneType."""
        from genro_builders.builder import _check_type

        assert _check_type(None, type(None)) is True
        assert _check_type("not none", type(None)) is False


# =============================================================================
# Tests for _split_annotated with Optional
# =============================================================================


class TestSplitAnnotated:
    """Tests for _split_annotated internal function."""

    def test_optional_annotated_type(self):
        """_split_annotated handles Optional[Annotated[T, ...]]."""
        from typing import Optional

        from genro_builders.builder import _split_annotated

        # Optional[Annotated[int, Range(ge=0)]] is Union[Annotated[int, Range(ge=0)], None]
        tp = Optional[Annotated[int, Range(ge=0)]]
        base, validators = _split_annotated(tp)

        assert base == int
        assert len(validators) == 1
        assert isinstance(validators[0], Range)


# =============================================================================
# Tests for _parse_sub_tags_spec
# =============================================================================


class TestParseSubTagsSpec:
    """Tests for _parse_sub_tags_spec internal function."""

    def test_range_syntax(self):
        """_parse_sub_tags_spec handles [min:max] syntax."""
        from genro_builders.builder import _parse_sub_tags_spec

        result = _parse_sub_tags_spec("item[1:3]")
        assert result == {"item": (1, 3)}

        result = _parse_sub_tags_spec("item[0:]")
        import sys

        assert result == {"item": (0, sys.maxsize)}

        result = _parse_sub_tags_spec("item[:5]")
        assert result == {"item": (0, 5)}

    def test_invalid_empty_brackets_raises(self):
        """_parse_sub_tags_spec raises for invalid [] syntax."""
        from genro_builders.builder import _parse_sub_tags_spec

        with pytest.raises(ValueError, match="Invalid sub_tags syntax"):
            _parse_sub_tags_spec("item[]")


# =============================================================================
# Tests for _pop_decorated_methods tags tuple
# =============================================================================


class TestPopDecoratedMethodsTags:
    """Tests for _pop_decorated_methods with tuple tags."""

    def test_element_with_tags_tuple(self):
        """@element with tags as tuple."""

        class Builder(BagBuilderBase):
            @element(tags=("alias1", "alias2"))
            def _internal(self): ...

        # Both aliases should be in schema
        assert Builder._class_schema.get_node("alias1") is not None
        assert Builder._class_schema.get_node("alias2") is not None
