# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Emitter tests: turn a source tree into .py, and close the round-trip.

The emitter is the third face of the single pivot: source tree -> Python
that recreates it. Combined with the reader, it closes the loop
.xsd -> reader -> emitter -> .py -> render -> .xsd', which must be
equipollent to the original (validates the same documents; here, even
byte-identical for the covered subset).
"""
from __future__ import annotations

import pytest
import xmlschema

from genro_builders.contrib.xsd import XsdBuilder
from genro_builders.contrib.xsd.emitter import XsdEmitter
from genro_builders.contrib.xsd.reader import XsdReader

XS = "http://www.w3.org/2001/XMLSchema"

PERSON = (
    f'<xs:schema xmlns:xs="{XS}" targetNamespace="urn:demo" '
    'elementFormDefault="qualified">'
    '<xs:element name="Person"><xs:complexType><xs:sequence>'
    '<xs:element name="Name" type="xs:string"/>'
    '<xs:element name="Age" type="xs:integer" minOccurs="0"/>'
    "</xs:sequence></xs:complexType></xs:element></xs:schema>"
)


def _mounted(builder):
    """Mount a fresh builder and return it (add_builder runs its main)."""
    builder.create()
    return builder


def test_emit_produces_runnable_source():
    """The emitted .py is valid Python declaring class_name(XsdBuilder)."""
    b = XsdReader(XsdBuilder()).read(PERSON)
    src = XsdEmitter(b).emit(class_name="PersonSchema")
    assert "class PersonSchema(XsdBuilder):" in src
    assert "def main(self, root):" in src
    assert "root.schema(" in src
    assert ".element(name='Person')" in src
    assert ".sequence(" in src
    # It compiles.
    compile(src, "<emitted>", "exec")


def test_emit_literal_one_call_per_node():
    """Literal transcription: a call for every node, containers get a var."""
    b = XsdReader(XsdBuilder()).read(PERSON)
    src = XsdEmitter(b).emit()
    # Two leaf elements inside the sequence -> two element() calls on it.
    assert src.count(".element(") == 3  # Person + Name + Age
    assert "complexType_0 =" in src
    assert "sequence_0 =" in src


def test_components_true_not_implemented():
    """components=True is an explicit error until the semantic pass exists."""
    b = XsdReader(XsdBuilder()).read(PERSON)
    with pytest.raises(NotImplementedError, match="components"):
        XsdEmitter(b).emit(components=True)


def test_roundtrip_equipollence():
    """.xsd -> reader -> emitter -> .py -> render -> .xsd' is equipollent:
    both schemas validate the same document (and here render-identical)."""
    b1 = XsdReader(XsdBuilder()).read(PERSON)
    src = XsdEmitter(b1).emit(class_name="RT")

    ns: dict = {}
    exec(compile(src, "<emitted>", "exec"), ns)  # noqa: S102 - generated, trusted
    b2 = _mounted(ns["RT"]())

    original = b1.render(target=False)
    regenerated = b2.render(target=False)

    doc = '<Person xmlns="urn:demo"><Name>A</Name><Age>1</Age></Person>'
    assert xmlschema.XMLSchema(original).is_valid(doc)
    assert xmlschema.XMLSchema(regenerated).is_valid(doc)
    assert original == regenerated  # equipollent, byte-identical here


def test_roundtrip_with_simpletype_restriction():
    """Round-trip a schema with a restricted simpleType stays equipollent."""
    xsd = (
        f'<xs:schema xmlns:xs="{XS}">'
        '<xs:simpleType name="Freq"><xs:restriction base="xs:string">'
        '<xs:enumeration value="daily"/><xs:enumeration value="weekly"/>'
        "</xs:restriction></xs:simpleType></xs:schema>"
    )
    b1 = XsdReader(XsdBuilder()).read(xsd)
    src = XsdEmitter(b1).emit(class_name="Freq")
    ns: dict = {}
    exec(compile(src, "<emitted>", "exec"), ns)  # noqa: S102
    b2 = _mounted(ns["Freq"]())
    assert b1.render(target=False) == b2.render(target=False)
