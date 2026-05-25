# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Intermediate model for the XSD codegen pipeline.

Parser-neutral dataclasses populated by a backend (currently
:class:`XmlschemaBackend`) and consumed by a generator (currently
:class:`PythonGenerator`). The model is the contract between the two
halves of the pipeline: adding a new backend (e.g. RelaxNG) or a new
generator (e.g. JSON schema, doc page) does not require changing the
other half.

The model intentionally records every XSD constraint the backend
observes, including those the current builder grammar does not yet
emit as validators (``min_length``, ``max_length``, ``total_digits``,
``fraction_digits``). Storing them keeps the model honest and lets a
future grammar extension pick them up without re-parsing the XSD.

Predisposed for multi-namespace via ``NamespaceModel.imports``. The
current backend does not populate it (single-namespace XSD only);
``xs:import`` raises a warning in the backend.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class NamespaceRef:
    """Reference to an external XSD namespace (e.g. via ``xs:import``)."""

    uri: str
    prefix: str | None = None


@dataclass
class SimpleConstraint:
    """Restrictions of an XSD simple type.

    ``base`` is the abstract category used by the generator to pick a
    Python type (see ``PythonGenerator._python_type_for``). Numeric
    bounds use :class:`~decimal.Decimal` to preserve XSD precision.
    """

    base: str  # "string" | "int" | "decimal" | "bool" | "enum"
    pattern: str | None = None
    enum_values: list[str] | None = None
    min_length: int | None = None
    max_length: int | None = None
    min_inclusive: Decimal | None = None
    max_inclusive: Decimal | None = None
    total_digits: int | None = None
    fraction_digits: int | None = None


@dataclass
class AttributeModel:
    """An XSD attribute on a complex type."""

    name: str
    required: bool = False
    constraint: SimpleConstraint | None = None


@dataclass
class ChildModel:
    """A child element occurrence in a complex type's content model.

    Cardinality bounds collapse the XSD model groups (sequence /
    choice / all) into a flat per-tag (min, max). ``max_occurs=None``
    means ``unbounded``.
    """

    name: str
    min_occurs: int = 1
    max_occurs: int | None = 1


@dataclass
class ElementModel:
    """A global element definition translated into builder grammar.

    Children are flattened (model groups collapsed). The order of
    ``children`` reflects the document order in the XSD; downstream
    consumers should treat it as documentation, not as an ordering
    constraint enforced by the builder grammar.
    """

    name: str
    children: list[ChildModel] = field(default_factory=list)
    attrs: list[AttributeModel] = field(default_factory=list)
    text_constraint: SimpleConstraint | None = None  # simpleContent
    documentation: str | None = None


@dataclass
class NamespaceModel:
    """All elements declared under a single XSD ``targetNamespace``."""

    target_namespace: str | None = None
    imports: list[NamespaceRef] = field(default_factory=list)
    elements: list[ElementModel] = field(default_factory=list)

    def find_element(self, name: str) -> ElementModel | None:
        """Look up an element by name (linear scan; the model is small)."""
        for el in self.elements:
            if el.name == name:
                return el
        return None


if __name__ == "__main__":
    # Smoke-test: build a tiny model by hand and print a summary.
    model = NamespaceModel(
        target_namespace="http://example.com/demo",
        elements=[
            ElementModel(
                name="Greeting",
                children=[ChildModel(name="Subject", min_occurs=1, max_occurs=1)],
                attrs=[
                    AttributeModel(
                        name="lang",
                        required=True,
                        constraint=SimpleConstraint(base="string"),
                    )
                ],
            ),
            ElementModel(name="Subject", text_constraint=SimpleConstraint(base="string")),
        ],
    )
    print(f"targetNamespace = {model.target_namespace}")
    print(f"elements = {[el.name for el in model.elements]}")
    print(f"Greeting -> {model.find_element('Greeting')}")
