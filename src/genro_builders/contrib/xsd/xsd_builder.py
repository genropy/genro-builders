# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""XsdBuilder — XSD 1.0 dialect for genro-builders.

The grammar is the XSD vocabulary from ``XsdElements`` (every element
prefixed ``xs:`` via ``ns="xs"``). An XSD schema is XML, so rendering is
the core ``XmlRenderer`` (inherited ``renderer_xml``): no dialect-specific
renderer. The ``xs`` prefix is bound once by the user as an ``xmlns_xs``
attribute on the ``schema`` root.

This is the pure, application-agnostic XSD grammar: it knows how to write
any schema, nothing about Genropy or widgets. A downstream layer
(``GnrXsdBuilder``, outside this repo) subclasses it to add its own
``xs:appinfo`` vocabulary (an ``<editor>`` describing a form widget).

Example::

    from genro_builders.builder import BuilderHandler
    from genro_builders.contrib.xsd import XsdBuilder

    XS = "http://www.w3.org/2001/XMLSchema"

    class MySchema(XsdBuilder):
        def main(self, root):
            schema = root.schema(xmlns_xs=XS, targetNamespace="urn:demo")
            el = schema.element(name="Consultorio", type="xs:string")

    doc = MySchema()
    BuilderHandler().add_builder(doc)
    doc.create()
    print(doc.render(target=False, doc_header=True))
"""

from __future__ import annotations

from genro_builders.xml import XmlBuilderBase

from .xsd_elements import XsdElements


class XsdBuilder(XmlBuilderBase, XsdElements):
    """XSD 1.0 dialect builder. Grammar only — rendering on the core
    ``XmlRenderer`` via the inherited ``renderer_xml`` property."""

    _name = "xsd"


if __name__ == "__main__":
    from genro_builders.builder import BuilderHandler

    XS = "http://www.w3.org/2001/XMLSchema"

    class _Demo(XsdBuilder):
        def main(self, root):
            schema = root.schema(xmlns_xs=XS, targetNamespace="urn:demo")
            schema.element(name="Consultorio", type="xs:string")

    page = _Demo()
    BuilderHandler().add_builder(page)
    page.create()
    print(page.render(target=False, doc_header=True, pretty=True))
