# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""XSD contrib — write XSD 1.0 schemas pythonically.

An XSD schema is XML, so it renders through the core ``XmlRenderer`` with
no new renderer. :class:`XsdBuilder` carries the grammar: the XSD
vocabulary declared with ``ns="xs"`` so ``sequence`` emits
``<xs:sequence>``. The builder is mounted on the generic
``BuilderHandler`` like any other dialect.

``XsdBuilder`` is pure and application-agnostic. A downstream layer adds
form-widget vocabularies inside ``xs:appinfo``.

Example::

    from genro_builders.builder import BuilderHandler
    from genro_builders.contrib.xsd import XsdBuilder

    XS = "http://www.w3.org/2001/XMLSchema"

    class MySchema(XsdBuilder):
        def main(self, root):
            root.schema(xmlns_xs=XS).element(name="Foo", type="xs:string")

    doc = MySchema()
    BuilderHandler().add_builder(doc)
    doc.create()
    print(doc.render(target=False, doc_header=True))
"""

from __future__ import annotations

from .xsd_builder import XsdBuilder

__all__ = ["XsdBuilder"]
