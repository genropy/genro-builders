# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Reader tests: import an existing .xsd into an XsdBuilder source tree.

The reader is the reverse of rendering: it parses a schema and rebuilds
it inside a builder, so the populated source tree can be rendered back
(equipollence check) or emitted as .py. It is grammar-parametric — the
given builder's grammar resolves every tag; an unknown tag is a loud
error. Application-namespace elements (an ``<editor>`` inside appinfo)
are preserved when the grammar knows them, prefix binding included.
"""
from __future__ import annotations

import pytest

from genro_builders.builder import element as el
from genro_builders.contrib.xsd import XsdBuilder
from genro_builders.contrib.xsd.reader import XsdReader

XS = "http://www.w3.org/2001/XMLSchema"


class _GnrXsdBuilder(XsdBuilder):
    """Simulates a downstream dialect: XsdBuilder + an ``editor`` element
    in its own application namespace (prefix ``ed``)."""

    _name = "gnrxsdtest"

    @el(sub_tags="", ns="ed")
    def editor(self, **kwargs): ...


def test_roundtrip_pure_xsd():
    xsd = (
        f'<xs:schema xmlns:xs="{XS}" targetNamespace="urn:demo" '
        'elementFormDefault="qualified">'
        '<xs:element name="Person"><xs:complexType><xs:sequence>'
        '<xs:element name="Name" type="xs:string"/>'
        '<xs:element name="Age" type="xs:integer" minOccurs="0"/>'
        '</xs:sequence></xs:complexType></xs:element>'
        "</xs:schema>"
    )
    out = XsdReader(XsdBuilder()).read(xsd).render(target=False)
    assert f'xmlns:xs="{XS}"' in out
    assert 'targetNamespace="urn:demo"' in out
    assert '<xs:element name="Person">' in out
    assert "<xs:complexType>" in out
    assert "<xs:sequence>" in out
    assert '<xs:element name="Name" type="xs:string">' in out
    assert '<xs:element name="Age" type="xs:integer" minOccurs="0">' in out


def test_roundtrip_import_keyword_tag():
    """``<xs:import>`` (Python-keyword local name) round-trips."""
    xsd = (
        f'<xs:schema xmlns:xs="{XS}">'
        '<xs:import namespace="urn:ext" schemaLocation="ext.xsd"/>'
        "</xs:schema>"
    )
    out = XsdReader(XsdBuilder()).read(xsd).render(target=False)
    assert '<xs:import namespace="urn:ext" schemaLocation="ext.xsd">' in out


def test_roundtrip_simpletype_restriction_enum():
    xsd = (
        f'<xs:schema xmlns:xs="{XS}">'
        '<xs:simpleType name="Freq"><xs:restriction base="xs:string">'
        '<xs:enumeration value="daily"/><xs:enumeration value="weekly"/>'
        "</xs:restriction></xs:simpleType></xs:schema>"
    )
    out = XsdReader(XsdBuilder()).read(xsd).render(target=False)
    assert '<xs:restriction base="xs:string">' in out
    assert '<xs:enumeration value="daily">' in out
    assert '<xs:enumeration value="weekly">' in out


def test_application_namespace_preserved_with_grammar():
    """An ``<editor>`` in its own namespace is preserved when the given
    grammar declares it, with its ``xmlns`` binding re-declared."""
    xsd = (
        f'<xs:schema xmlns:xs="{XS}" targetNamespace="urn:demo">'
        '<xs:element name="Consultorio" type="xs:string"><xs:annotation><xs:appinfo>'
        '<ed:editor xmlns:ed="urn:demetra:editor:1.0" widget="dbselect" '
        'dbtable="dmt_base.consultorio" relation_field="codice"/>'
        "</xs:appinfo></xs:annotation></xs:element></xs:schema>"
    )
    out = XsdReader(_GnrXsdBuilder()).read(xsd).render(target=False)
    assert "<xs:annotation>" in out
    assert "<xs:appinfo>" in out
    assert '<ed:editor' in out
    assert 'widget="dbselect"' in out
    assert 'relation_field="codice"' in out  # underscore attr verbatim
    assert 'xmlns:ed="urn:demetra:editor:1.0"' in out  # binding re-declared


def test_unknown_tag_is_loud_error():
    """A tag the given grammar does not know raises (no silent preserve).
    Pure XsdBuilder does not know ``editor``."""
    xsd = (
        f'<xs:schema xmlns:xs="{XS}">'
        '<xs:element name="X"><xs:annotation><xs:appinfo>'
        '<ed:editor xmlns:ed="urn:demetra:editor:1.0" widget="dbselect"/>'
        "</xs:appinfo></xs:annotation></xs:element></xs:schema>"
    )
    with pytest.raises(ValueError, match="not in the grammar"):
        XsdReader(XsdBuilder()).read(xsd)


def test_reader_from_path(tmp_path):
    """The reader accepts a filesystem path, not only a raw string."""
    xsd = f'<xs:schema xmlns:xs="{XS}"><xs:element name="Foo" type="xs:string"/></xs:schema>'
    p = tmp_path / "schema.xsd"
    p.write_text(xsd)
    out = XsdReader(XsdBuilder()).read(p).render(target=False)
    assert '<xs:element name="Foo" type="xs:string">' in out
