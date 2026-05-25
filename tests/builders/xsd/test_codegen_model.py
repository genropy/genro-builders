# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for the codegen intermediate model.

Pure dataclass / no parser dependency: these tests must work without
``xmlschema`` installed.
"""

from __future__ import annotations

from decimal import Decimal

from genro_builders.contrib.xsd.codegen import (
    AttributeModel,
    ChildModel,
    ElementModel,
    NamespaceModel,
    NamespaceRef,
    SimpleConstraint,
)


def test_namespace_model_defaults_are_empty():
    model = NamespaceModel()
    assert model.target_namespace is None
    assert model.imports == []
    assert model.elements == []


def test_find_element_returns_none_when_missing():
    model = NamespaceModel()
    assert model.find_element("Foo") is None


def test_find_element_returns_the_match():
    foo = ElementModel(name="Foo")
    model = NamespaceModel(elements=[foo])
    assert model.find_element("Foo") is foo


def test_simple_constraint_carries_facets_verbatim():
    c = SimpleConstraint(
        base="decimal",
        min_inclusive=Decimal("0"),
        max_inclusive=Decimal("9999"),
        total_digits=4,
        fraction_digits=2,
    )
    assert c.base == "decimal"
    assert c.min_inclusive == Decimal("0")
    assert c.max_inclusive == Decimal("9999")
    assert c.total_digits == 4
    assert c.fraction_digits == 2


def test_element_with_children_and_attrs():
    el = ElementModel(
        name="Doc",
        children=[
            ChildModel(name="Head", min_occurs=1, max_occurs=1),
            ChildModel(name="Body", min_occurs=1, max_occurs=None),
        ],
        attrs=[
            AttributeModel(name="version", required=True, constraint=SimpleConstraint(base="string")),
        ],
    )
    assert el.children[1].max_occurs is None  # unbounded
    assert el.attrs[0].required is True


def test_namespace_ref_carries_uri_only():
    ref = NamespaceRef(uri="http://example.com/x")
    assert ref.uri == "http://example.com/x"
    assert ref.prefix is None
