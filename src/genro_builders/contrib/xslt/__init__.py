# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""XSLT contrib — write XSLT 1.0 stylesheets pythonically.

An XSLT stylesheet is XML, so it renders through the core ``XmlRenderer``
with no new renderer. :class:`XsltBuilder` carries the grammar (XSLT
instructions declared with ``_meta`` ``ns``/``local`` so ``for_each``
emits ``<xsl:for-each>``, plus literal result elements emitted verbatim);
:class:`XsltBuilderHandler` is the engine preset.

Example::

    from genro_builders.contrib.xslt import XsltBuilderHandler

    XSL = "http://www.w3.org/1999/XSL/Transform"

    class SitemapToHtml(XsltBuilderHandler):
        def main(self, root):
            ss = root.stylesheet(version="1.0", xmlns_xsl=XSL)
            ss.output(method="html")
            tpl = ss.template(match="/urlset")
            tpl.html().body().h1("Sitemap")

    sheet = SitemapToHtml()
    sheet.create()
    print(sheet.render(target=False, doc_header=True))
"""

from __future__ import annotations

from .xslt_builder import XsltBuilder, XsltBuilderHandler

__all__ = [
    "XsltBuilder",
    "XsltBuilderHandler",
]
