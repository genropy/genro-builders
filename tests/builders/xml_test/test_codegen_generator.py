# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for the codegen Python generator.

The generator is exercised against hand-built models (no XSD parser
required), so these tests run without ``xmlschema`` installed.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from genro_builders.xml.transpiler import (
    AttributeModel,
    ChildModel,
    ElementModel,
    NamespaceModel,
    PythonGenerator,
    SimpleConstraint,
)


@pytest.fixture
def gen():
    return PythonGenerator()


def test_empty_model_yields_builder_and_handler_classes(gen):
    model = NamespaceModel(target_namespace="http://example.com/x")
    src = gen.render(model, "Demo")
    assert "class DemoBuilder(XmlBuilderBase):" in src
    assert "class DemoHandler(XmlHandler):" in src
    assert "builder_class = DemoBuilder" in src
    assert "from genro_builders.builder import element" in src
    assert "from genro_builders.xml import XmlBuilderBase, XmlHandler" in src
    assert "GENERATED FILE" in src


def test_leaf_element_no_subtags_no_attrs(gen):
    model = NamespaceModel(elements=[ElementModel(name="Empty")])
    src = gen.render(model, "Demo")
    assert "@element()\n    def Empty(self):" in src


def test_subtags_collapse_cardinalities(gen):
    model = NamespaceModel(
        elements=[
            ElementModel(
                name="Doc",
                children=[
                    ChildModel(name="Head", min_occurs=1, max_occurs=1),
                    ChildModel(name="Body", min_occurs=1, max_occurs=None),
                    ChildModel(name="Foot", min_occurs=0, max_occurs=1),
                ],
            ),
        ],
    )
    src = gen.render(model, "Demo")
    assert "sub_tags='Head[1],Body[1:],Foot[0:1]'" in src


def test_enum_attribute_yields_literal(gen):
    model = NamespaceModel(
        elements=[
            ElementModel(
                name="Foo",
                attrs=[
                    AttributeModel(
                        name="kind",
                        required=True,
                        constraint=SimpleConstraint(
                            base="enum",
                            enum_values=["A", "B", "C"],
                        ),
                    ),
                ],
            ),
        ],
    )
    src = gen.render(model, "Demo")
    assert "from typing import" in src and "Literal" in src
    assert "kind: Literal['A', 'B', 'C'] | None = None" in src


def test_regex_pattern_yields_annotated_regex(gen):
    model = NamespaceModel(
        elements=[
            ElementModel(
                name="Foo",
                text_constraint=SimpleConstraint(
                    base="string",
                    pattern="[A-Z]{3}",
                ),
            ),
        ],
    )
    src = gen.render(model, "Demo")
    assert "Annotated" in src
    assert "Regex('[A-Z]{3}')" in src
    assert "from genro_builders.builder import Regex, element" in src


def test_range_min_max_yields_annotated_range(gen):
    model = NamespaceModel(
        elements=[
            ElementModel(
                name="Foo",
                attrs=[
                    AttributeModel(
                        name="qty",
                        constraint=SimpleConstraint(
                            base="decimal",
                            min_inclusive=Decimal("1"),
                            max_inclusive=Decimal("99"),
                        ),
                    ),
                ],
            ),
        ],
    )
    src = gen.render(model, "Demo")
    assert "Range(ge=1.0, le=99.0)" in src
    assert "from decimal import Decimal" in src
    assert "from genro_builders.builder import Range, element" in src


def test_grammar_gap_constraints_surface_as_comment_notes(gen):
    model = NamespaceModel(
        elements=[
            ElementModel(
                name="Foo",
                text_constraint=SimpleConstraint(
                    base="string",
                    min_length=2,
                    max_length=5,
                ),
                attrs=[
                    AttributeModel(
                        name="amount",
                        constraint=SimpleConstraint(
                            base="decimal",
                            total_digits=10,
                            fraction_digits=2,
                        ),
                    ),
                ],
            ),
        ],
    )
    src = gen.render(model, "Demo")
    assert "NOTE: node_value: length [2..5] not emitted (grammar gap)" in src
    assert "NOTE: amount: totalDigits=10 not emitted (grammar gap)" in src
    assert "NOTE: amount: fractionDigits=2 not emitted (grammar gap)" in src


def test_render_is_deterministic(gen):
    model = NamespaceModel(
        elements=[
            ElementModel(
                name="Foo",
                children=[ChildModel(name="Bar", min_occurs=1, max_occurs=1)],
            ),
            ElementModel(name="Bar"),
        ],
    )
    src_a = gen.render(model, "Demo")
    src_b = gen.render(model, "Demo")
    assert src_a == src_b


def test_unknown_tag_names_are_slugged(gen):
    """A tag like ``my-tag`` is not a valid Python identifier; the
    generator must alias it via ``@element(tags='my-tag')``."""
    model = NamespaceModel(elements=[ElementModel(name="my-tag")])
    src = gen.render(model, "Demo")
    assert "tags='my-tag'" in src
    assert "def my_tag(self):" in src


def test_generated_module_is_executable_and_renders(gen):
    """The generated source compiles, its handler builds a document, and
    a real ``xml`` render walks the grammar end to end."""
    model = NamespaceModel(
        target_namespace="http://example.com/demo",
        elements=[
            ElementModel(
                name="Greeting",
                children=[ChildModel(name="Subject", min_occurs=1, max_occurs=1)],
            ),
            ElementModel(name="Subject"),
        ],
    )
    src = gen.render(model, "Demo")
    namespace: dict[str, object] = {}
    exec(compile(src, "<generated>", "exec"), namespace)
    handler_class = namespace["DemoHandler"]

    class MyDoc(handler_class):  # type: ignore[valid-type, misc]
        def main(self, root):
            root.Greeting().Subject("hi")

    doc = MyDoc()
    doc.create()
    assert doc.render(mode="xml", target=False) == (
        "<Greeting><Subject>hi</Subject></Greeting>"
    )
