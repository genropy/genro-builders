# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""XsltBuilder — XSLT 1.0 dialect for genro-builders.

The grammar comes from ``XsltElements`` (XSLT instructions + literal
result elements). Rendering is the core ``XmlRenderer`` (an XSLT
stylesheet is XML): no dialect-specific renderer. The ``xsl:`` prefixes
are composed at render time from the elements' ``_meta`` and the
``xmlns_xsl`` declaration on the stylesheet root.
"""

from __future__ import annotations

from ..xml.xml_builder import XmlBuilderBase, XmlHandler
from .xslt_elements import XsltElements


class XsltBuilder(XmlBuilderBase, XsltElements):
    """XSLT 1.0 dialect builder. Grammar only — rendering on the core
    ``XmlRenderer`` via the inherited ``renderer_xml`` property."""

    _name = "xslt"


class XsltBuilderHandler(XmlHandler):
    """Preset handler bound to :class:`XsltBuilder`."""

    builder_class = XsltBuilder


if __name__ == "__main__":
    handler = XsltBuilderHandler()
    handler.create()
    print(handler.render(target=False))
