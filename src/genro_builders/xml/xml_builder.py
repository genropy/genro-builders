# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""XmlBuilderBase — shared grammar base for XML-on-the-wire dialects.

A growing family of dialects serialize to XML: schemas (XSD), transforms
(XSLT), and any future XML vocabulary. They share one trait the markup
dialects (HTML/SVG/CSS) do not need — XML namespaces, where a prefixed
tag like ``xsl:value-of`` is composed at render time from an element's
``_meta`` (``ns``/``local``) and a namespace declared as an
``xmlns_<prefix>`` attribute. That mechanism lives on the core
``XmlRenderer``; what these two bases add is the semantic anchor: a
single place to fix ``xml`` as the default render mode for the family.

These bases are intentionally light. The real XML render is the core's
``XmlRenderer`` (on ``RendererBase``, exposed by
``BuilderBase.renderer_xml``): every dialect already serves ``xml``
with pointers resolved and framework markers filtered.
"""

from __future__ import annotations

from genro_builders.builder import BuilderBase


class XmlBuilderBase(BuilderBase):
    """Grammar base for dialects whose on-the-wire format is XML.

    The default render mode is ``xml``. Concrete dialects (``XsltBuilder``,
    the schema-generated ``SitemapBuilder``/``FatturaElettronicaBuilder``,
    ...) subclass this and add their ``@element`` vocabulary. Left
    unregistered (``_name = None``): it is an abstract anchor, not a
    usable dialect.
    """

    _default_render_mode = "xml"


if __name__ == "__main__":
    builder = XmlBuilderBase
    print(f"{builder.__name__} default mode: {builder._default_render_mode}")
