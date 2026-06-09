# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""XSLT contrib — write XSLT 1.0 stylesheets pythonically.

An XSLT stylesheet is XML, so it renders through the core ``XmlRenderer``
with no new renderer. :class:`XsltBuilder` carries the grammar: the XSLT
instructions (declared with ``_meta['render_tag']`` so ``for_each`` emits
``<xslt:for-each>``) plus the whole HTML5 vocabulary mixed in as literal
result elements, emitted verbatim. The ``output``/``template``
instructions are named ``xslt_output``/``xslt_template`` to leave the bare
names for the HTML ``<output>``/``<template>`` tags. The builder is
mounted on the generic ``BuilderHandler`` like any other dialect.

Example::

    from genro_builders.builder import BuilderHandler
    from genro_builders.contrib.xslt import XsltBuilder

    XSL = "http://www.w3.org/1999/XSL/Transform"

    class SitemapToHtml(XsltBuilder):
        def main(self, root):
            ss = root.stylesheet(version="1.0", xmlns_xslt=XSL)
            ss.xslt_output(method="html")
            tpl = ss.xslt_template(match="/urlset")
            tpl.html().body().h1("Sitemap")

    sheet = SitemapToHtml()
    BuilderHandler().add_builder(main=sheet)
    sheet.create()
    print(sheet.render(target=False, doc_header=True))
"""

from __future__ import annotations

from .xslt_builder import XsltBuilder

__all__ = [
    "XsltBuilder",
]
