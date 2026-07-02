# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Emitter idiomatic-style tests: readable Python, equipollent XSD.

``style="idiomatic"`` trades the literal transcription's byte-identical
guarantee for a semantic one: same named types, same structure inside
each, regardless of declaration order or variable naming. Exercised on
the real FatturaPA schema (the actual stress case that motivated the
style), not a minimal fixture — that schema is what proved the literal
form unreadable in the first place.
"""
from __future__ import annotations

from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from genro_builders.builder import BuilderHandler
from genro_builders.contrib.xsd import XsdBuilder
from genro_builders.contrib.xsd.emitter import XsdEmitter
from genro_builders.contrib.xsd.reader import XsdReader

FATTURAPA = (
    Path(__file__).parents[1]
    / "src/genro_builders/xml/examples/fatturapa/Schema_VFPA12_V1.2.3.xsd"
)

XS = "http://www.w3.org/2001/XMLSchema"
PERSON = (
    f'<xs:schema xmlns:xs="{XS}" targetNamespace="urn:demo" '
    'elementFormDefault="qualified">'
    '<xs:element name="Person"><xs:complexType><xs:sequence>'
    '<xs:element name="Name" type="xs:string"/>'
    '<xs:element name="Age" type="xs:integer" minOccurs="0"/>'
    "</xs:sequence></xs:complexType></xs:element></xs:schema>"
)

ENUM_XSD = (
    f'<xs:schema xmlns:xs="{XS}">'
    '<xs:simpleType name="Freq"><xs:restriction base="xs:string">'
    '<xs:enumeration value="daily"><xs:annotation>'
    "<xs:documentation>Once a day</xs:documentation></xs:annotation>"
    "</xs:enumeration>"
    '<xs:enumeration value="weekly"><xs:annotation>'
    "<xs:documentation>Once a week</xs:documentation></xs:annotation>"
    "</xs:enumeration>"
    "</xs:restriction></xs:simpleType></xs:schema>"
)

TYPED_ELEMENT_XSD = (
    f'<xs:schema xmlns:xs="{XS}">'
    '<xs:element name="Root" type="RootType"/>'
    '<xs:complexType name="RootType"><xs:sequence>'
    '<xs:element name="Item" type="ItemType"/>'
    "</xs:sequence></xs:complexType>"
    '<xs:complexType name="ItemType"><xs:sequence>'
    '<xs:element name="Value" type="xs:string"/>'
    "</xs:sequence></xs:complexType>"
    "</xs:schema>"
)


def _mounted(builder):
    BuilderHandler().add_builder(builder)
    return builder


def _strip(tag: str) -> str:
    return tag.split("}")[-1]


def _named_type_structure(xsd_text: str) -> dict[tuple[str, str | None], list]:
    """Map (tag, name) -> recursive (tag, attrs, text, children) summary
    for every named complexType/simpleType at schema level."""
    root = ET.fromstring(xsd_text)

    def summarize(node):
        return [
            (_strip(c.tag), tuple(sorted(c.attrib.items())), (c.text or "").strip() or None, summarize(c))
            for c in node
        ]

    return {
        (_strip(child.tag), child.get("name")): summarize(child)
        for child in root
        if _strip(child.tag) in ("complexType", "simpleType") and child.get("name")
    }


def test_idiomatic_style_compiles():
    b = XsdReader(XsdBuilder()).read(PERSON)
    src = XsdEmitter(b).emit(class_name="PersonSchema", style="idiomatic")
    assert "class PersonSchema(XsdBuilder):" in src
    compile(src, "<emitted>", "exec")


def test_unknown_style_raises():
    b = XsdReader(XsdBuilder()).read(PERSON)
    with pytest.raises(ValueError, match="unknown style"):
        XsdEmitter(b).emit(style="fancy")


def test_idiomatic_semantic_naming():
    """Variable names come from the node's name/type, not a counter."""
    b = XsdReader(XsdBuilder()).read(PERSON)
    src = XsdEmitter(b).emit(class_name="PersonSchema", style="idiomatic")
    assert "element_0" not in src
    assert "person" in src.lower()


def test_idiomatic_chaining_collapses_single_use():
    """A restriction with one enumeration (below the 2-item threshold)
    chains into a single call, no intermediate variables."""
    xsd = (
        f'<xs:schema xmlns:xs="{XS}">'
        '<xs:simpleType name="Freq"><xs:restriction base="xs:string">'
        '<xs:enumeration value="daily"/>'
        "</xs:restriction></xs:simpleType></xs:schema>"
    )
    b = XsdReader(XsdBuilder()).read(xsd)
    src = XsdEmitter(b).emit(class_name="Freq", style="idiomatic")
    assert "restriction_0 =" not in src
    assert ".restriction(base='xs:string').enumeration(value='daily')" in src


def test_idiomatic_enumerated_helper():
    """3+ enumeration siblings collapse into self.enumerated(...)."""
    b = XsdReader(XsdBuilder()).read(ENUM_XSD)
    src = XsdEmitter(b).emit(class_name="Freq", style="idiomatic")
    assert src.count("def enumerated(") == 1
    assert "self.enumerated(" in src
    assert "('daily', 'Once a day')" in src
    compile(src, "<emitted>", "exec")


def test_idiomatic_component_per_type():
    """An element referencing a named type of the same schema becomes a
    call to that type's own @component alias."""
    b = XsdReader(XsdBuilder()).read(TYPED_ELEMENT_XSD)
    src = XsdEmitter(b).emit(class_name="Typed", style="idiomatic")
    assert "from genro_builders.builder import component" in src
    assert "@component" in src
    assert "def ItemType(self, root, name, **attrs):" in src
    assert ".ItemType(name='Item')" in src

    ns: dict = {}
    exec(compile(src, "<emitted>", "exec"), ns)  # noqa: S102 - generated, trusted
    b2 = _mounted(ns["Typed"]())
    rendered = b2.render(target=False)
    assert '<xs:element name="Item" type="ItemType"' in rendered or (
        "<xs:element name='Item' type='ItemType'" in rendered
    )


def test_idiomatic_complex_types_grouping_fatturapa():
    """Named complexType/simpleType are grouped into dedicated methods,
    regardless of their original interleaved position under schema."""
    b = XsdReader(XsdBuilder()).read(FATTURAPA)
    src = XsdEmitter(b).emit(class_name="FatturaElettronicaSchema", style="idiomatic")
    assert "def complex_types(self, schema):" in src
    assert "def simple_types(self, schema):" in src
    assert "self.complex_types(schema)" in src
    assert "self.simple_types(schema)" in src
    compile(src, "<emitted>", "exec")


def test_idiomatic_fatturapa_structural_equipollence():
    """The idiomatic .py, executed and rendered, has the exact same set
    of named types with the exact same internal structure as the
    literal round-trip — declaration order between types is free, but
    nothing is lost, added, or reshaped inside any type."""
    b1 = XsdReader(XsdBuilder()).read(FATTURAPA)
    literal_src = XsdEmitter(b1).emit(class_name="Literal", style="literal")
    ns1: dict = {}
    exec(compile(literal_src, "<emitted>", "exec"), ns1)  # noqa: S102
    b1_rebuilt = _mounted(ns1["Literal"]())
    original_render = b1_rebuilt.render(target=False)

    b2 = XsdReader(XsdBuilder()).read(FATTURAPA)
    idiomatic_src = XsdEmitter(b2).emit(class_name="Idiomatic", style="idiomatic")
    ns2: dict = {}
    exec(compile(idiomatic_src, "<emitted>", "exec"), ns2)  # noqa: S102
    b2_rebuilt = _mounted(ns2["Idiomatic"]())
    idiomatic_render = b2_rebuilt.render(target=False)

    original_types = _named_type_structure(original_render)
    idiomatic_types = _named_type_structure(idiomatic_render)

    assert set(original_types) == set(idiomatic_types)
    mismatched = [
        key for key in original_types if original_types[key] != idiomatic_types[key]
    ]
    assert not mismatched, f"structure mismatch for: {mismatched}"
