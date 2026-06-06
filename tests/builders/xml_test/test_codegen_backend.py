# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for the XmlschemaBackend.

These tests require the ``xmlschema`` package (extra ``[xsd]``).
They are skipped automatically when the dependency is missing, so the
suite remains green on a vanilla install.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pytest

xmlschema = pytest.importorskip("xmlschema")  # noqa: F401

from genro_builders.xml.transpiler import XmlschemaBackend  # noqa: E402
from genro_builders.xml.transpiler.backend import (  # noqa: E402
    XsdCodegenWarning,
    _as_decimal,
    _xsd_builtin_to_base,
)

MINIMAL_XSD = """<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           targetNamespace="http://example.com/demo"
           xmlns="http://example.com/demo"
           elementFormDefault="qualified">

  <xs:element name="Greeting">
    <xs:complexType>
      <xs:sequence>
        <xs:element name="Subject" type="xs:string" minOccurs="1" maxOccurs="1"/>
        <xs:element name="Body" type="xs:string" minOccurs="0" maxOccurs="unbounded"/>
      </xs:sequence>
      <xs:attribute name="lang" use="required">
        <xs:simpleType>
          <xs:restriction base="xs:string">
            <xs:enumeration value="it"/>
            <xs:enumeration value="en"/>
          </xs:restriction>
        </xs:simpleType>
      </xs:attribute>
    </xs:complexType>
  </xs:element>

  <xs:simpleType name="LimitedAmount">
    <xs:restriction base="xs:decimal">
      <xs:minInclusive value="0"/>
      <xs:maxInclusive value="9999.99"/>
      <xs:totalDigits value="6"/>
      <xs:fractionDigits value="2"/>
    </xs:restriction>
  </xs:simpleType>

  <xs:element name="Amount" type="LimitedAmount"/>
</xs:schema>
"""


@pytest.fixture
def xsd_file(tmp_path: Path) -> Path:
    f = tmp_path / "demo.xsd"
    f.write_text(MINIMAL_XSD)
    return f


@pytest.fixture
def model(xsd_file: Path):
    return XmlschemaBackend().load(xsd_file)


def test_target_namespace_is_recorded(model):
    assert model.target_namespace == "http://example.com/demo"


def test_top_level_elements_are_collected(model):
    names = {el.name for el in model.elements}
    assert {"Greeting", "Subject", "Body", "Amount"}.issubset(names)


def test_children_cardinalities_are_extracted(model):
    greeting = model.find_element("Greeting")
    assert greeting is not None
    by_name = {c.name: (c.min_occurs, c.max_occurs) for c in greeting.children}
    assert by_name["Subject"] == (1, 1)
    assert by_name["Body"] == (0, None)


def test_required_attribute_with_enum_constraint(model):
    greeting = model.find_element("Greeting")
    assert greeting is not None
    by_name = {a.name: a for a in greeting.attrs}
    lang = by_name["lang"]
    assert lang.required is True
    assert lang.constraint is not None
    assert lang.constraint.base == "enum"
    assert lang.constraint.enum_values == ["it", "en"]


def test_numeric_facets_are_extracted_on_simple_type(model):
    amount = model.find_element("Amount")
    assert amount is not None
    constraint = amount.text_constraint
    assert constraint is not None
    assert constraint.base == "decimal"
    assert constraint.min_inclusive is not None and float(constraint.min_inclusive) == 0.0
    assert constraint.max_inclusive is not None and float(constraint.max_inclusive) == 9999.99
    assert constraint.total_digits == 6
    assert constraint.fraction_digits == 2


def test_missing_xmlschema_raises_clear_error(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "xmlschema":
            raise ImportError("simulated")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(ImportError, match=r"genro-builders\[xsd\]"):
        XmlschemaBackend().load("anything.xsd")


def test_builtin_map_falls_back_to_string():
    assert _xsd_builtin_to_base("string") == "string"
    assert _xsd_builtin_to_base("decimal") == "decimal"
    assert _xsd_builtin_to_base("int") == "int"
    assert _xsd_builtin_to_base("unknownType") == "string"


def test_as_decimal_returns_none_on_non_numeric():
    # Plain numbers convert cleanly.
    assert _as_decimal(5) is not None
    assert _as_decimal("3.14") is not None
    # A non-numeric value (e.g. a date object) returns None instead of raising.

    class FakeDate:
        def __str__(self):
            return "1970-01-01"

    assert _as_decimal(FakeDate()) is None


def test_namespace_import_is_reported_with_warning(tmp_path: Path):
    aux = tmp_path / "aux.xsd"
    aux.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           targetNamespace="http://example.com/aux"
           elementFormDefault="qualified">
  <xs:element name="Aux" type="xs:string"/>
</xs:schema>
"""
    )
    main = tmp_path / "main.xsd"
    main.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"
           targetNamespace="http://example.com/main"
           xmlns:aux="http://example.com/aux"
           elementFormDefault="qualified">
  <xs:import namespace="http://example.com/aux" schemaLocation="aux.xsd"/>
  <xs:element name="Hello" type="xs:string"/>
</xs:schema>
"""
    )
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        model = XmlschemaBackend().load(main)
    warn_messages = [str(w.message) for w in recorded if issubclass(w.category, XsdCodegenWarning)]
    assert any("namespace import" in m for m in warn_messages)
    assert any(ref.uri == "http://example.com/aux" for ref in model.imports)
