# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Hierarchy, registration and rendering tests for the XSD dialect.

Verifies that ``XsdBuilder`` sits on the shared XML base, is registered
under ``xsd``, renders via the core ``XmlRenderer``, and that its grammar
composes ``xs:*`` tags through the ``ns="xs"`` parameter (no per-element
``render_tag``).
"""
from __future__ import annotations

from genro_builders.builder import BuilderBase, BuilderHandler
from genro_builders.contrib.xsd import XsdBuilder
from genro_builders.xml import XmlBuilderBase

XS = "http://www.w3.org/2001/XMLSchema"


def _render(main):
    """Mount a one-off ``XsdBuilder`` around ``main`` and return its XML."""

    class _S(XsdBuilder):
        pass

    _S.main = lambda self, root: main(root)
    doc = _S()
    BuilderHandler().add_builder(doc)
    return doc.render(target=False)


def test_xsd_builder_is_xml_base():
    assert issubclass(XsdBuilder, XmlBuilderBase)
    assert XsdBuilder._default_render_mode == "xml"


def test_xsd_registered():
    assert BuilderBase.get_builder_class("xsd") is XsdBuilder


def test_schema_root_composes_prefixed_tag_and_xmlns():
    out = _render(lambda root: root.schema(xmlns_xs=XS, targetNamespace="urn:demo"))
    assert f'<xs:schema xmlns:xs="{XS}" targetNamespace="urn:demo">' in out
    assert "</xs:schema>" in out


def test_element_and_attributes_verbatim():
    out = _render(
        lambda root: root.schema(xmlns_xs=XS).element(
            name="Consultorio", type="xs:string",
        )
    )
    assert '<xs:element name="Consultorio" type="xs:string">' in out


def test_complextype_sequence_nesting():
    def main(root):
        ct = root.schema(xmlns_xs=XS).element(name="Fattura").complexType()
        seq = ct.sequence()
        seq.element(name="Header", minOccurs="1", maxOccurs="1")

    out = _render(main)
    assert "<xs:complexType>" in out
    assert "<xs:sequence>" in out
    assert '<xs:element name="Header" minOccurs="1" maxOccurs="1">' in out


def test_simpletype_restriction_enumeration():
    def main(root):
        st = root.schema(xmlns_xs=XS).simpleType()
        r = st.restriction(base="xs:string")
        r.enumeration(value="daily")
        r.enumeration(value="weekly")

    out = _render(main)
    assert '<xs:restriction base="xs:string">' in out
    assert '<xs:enumeration value="daily"></xs:enumeration>' in out
    assert '<xs:enumeration value="weekly"></xs:enumeration>' in out


def test_import_keyword_method_emits_xs_import():
    """``import`` is a Python keyword: method ``import_`` -> ``xs:import``."""
    out = _render(
        lambda root: root.schema(xmlns_xs=XS).import_(
            namespace="urn:ext", schemaLocation="ext.xsd",
        )
    )
    assert '<xs:import namespace="urn:ext" schemaLocation="ext.xsd">' in out
    assert "import_" not in out


def test_ns_does_not_leak_as_attribute():
    """The ``ns`` grammar attribute is never emitted in the markup."""
    out = _render(lambda root: root.schema(xmlns_xs=XS).sequence())
    assert 'ns="xs"' not in out


def test_annotation_appinfo_render():
    """``annotation``/``appinfo`` are catch-all containers ready to host a
    downstream application vocabulary (``GnrXsdBuilder``, outside this
    repo). Here we only prove the pure XSD grammar emits them prefixed."""
    out = _render(
        lambda root: root.schema(xmlns_xs=XS).element(name="X").annotation().appinfo()
    )
    assert "<xs:annotation>" in out
    assert "<xs:appinfo></xs:appinfo>" in out
