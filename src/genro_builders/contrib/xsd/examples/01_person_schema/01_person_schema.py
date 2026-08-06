# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""01 — Person schema: write an XSD 1.0 schema pythonically.

What you learn:
    - An XSD schema is just XML, so it renders through the shared
      ``XmlRenderer`` — no XSD-specific renderer exists.
    - Every element declares ``ns="xs"``: the renderer composes the
      prefixed tag ``xs:<method-name>`` (``sequence`` -> ``xs:sequence``),
      so the ``xs`` prefix is declared once per element, never spelled
      out in a ``render_tag``.
    - The ``xs`` prefix is bound as a plain attribute on the root:
      ``schema(xmlns_xs=...)`` surfaces as ``xmlns:xs="..."``.
    - Structure (element, complexType, sequence), a simple element with a
      built-in type, and a restricted simpleType (enumeration) all read
      like the XSD they produce.

Prerequisites: None for the XSD dialect.

Usage:
    python 01_person_schema.py
"""
from __future__ import annotations

from pathlib import Path

from genro_builders.contrib.xsd import XsdBuilder

XS = "http://www.w3.org/2001/XMLSchema"


class PersonSchema(XsdBuilder):
    """A schema for a <Person> with a name, an age, and a gender enum."""

    def main(self, root):
        schema = root.schema(
            xmlns_xs=XS,
            targetNamespace="urn:example:person",
            elementFormDefault="qualified",
        )

        person = schema.element(name="Person")
        seq = person.complexType().sequence()
        seq.element(name="Name", type="xs:string")
        seq.element(name="Age", type="xs:integer", minOccurs="0")

        # Gender carries an inline simpleType: an enumeration restricting
        # xs:string. Inline (rather than a named global type) keeps the
        # example single-namespace and self-contained.
        gender = seq.element(name="Gender")
        restriction = gender.simpleType().restriction(base="xs:string")
        restriction.enumeration(value="male")
        restriction.enumeration(value="female")
        restriction.enumeration(value="other")


if __name__ == "__main__":
    page = PersonSchema()
    page.create()  # mounts and builds the source
    rendered = page.render(target=False, doc_header=True, pretty=True)

    output = Path("01_person_schema.xsd")
    output.write_text(rendered)
    print(rendered)
    print(f"\nSaved schema to {output}")
