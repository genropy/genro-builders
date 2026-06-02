# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""@element call-argument validation must work from the method signature.

A declarative ``@element`` declares its accepted call arguments through
its signature (parameter names, type hints, ``Annotated`` validators).
``__init_subclass__`` reads those via ``_extract_validators_from_signature``
into the schema's ``call_args_validations``, and ``_validate_call_args``
enforces them at call time.

Regression guard: the declarative marker returned by ``@element`` must
preserve the original signature so the extractor can read it. When the
marker dropped the function entirely, ``call_args_validations`` came out
empty and every annotated element silently skipped validation.
"""
from __future__ import annotations

from typing import Annotated

import pytest

from genro_builders.builder import BagBuilderBase, Regex, element


class _CountryBuilder(BagBuilderBase):
    _name = "test_country"
    _default_render_mode = "xml"

    @element(sub_tags="*")
    def root(self): ...

    @element(parent_tags="root")
    def country(
        self,
        node_value: Annotated[str, Regex("[A-Z]{2}")] | None = None,
    ): ...


def test_call_args_validations_extracted_from_signature():
    """An annotated @element must populate call_args_validations."""
    builder = _CountryBuilder()
    info = builder._get_schema_info("country")
    cav = info.get("call_args_validations")
    assert cav, "call_args_validations must not be empty for an annotated element"
    assert "node_value" in cav


def test_annotated_value_is_validated_at_call_time():
    """A value violating the element's Regex must raise at build time."""
    builder = _CountryBuilder()
    root = builder.new_root()
    node = root.root()
    with pytest.raises(ValueError, match="Validation failed"):
        node.country("XYZ")  # 3 chars violate [A-Z]{2}


def test_valid_value_passes():
    """A conforming value must not raise."""
    builder = _CountryBuilder()
    root = builder.new_root()
    node = root.root()
    node.country("IT")  # conforms to [A-Z]{2}
