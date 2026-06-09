# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""End-to-end test: a sitemap->HTML stylesheet written with the XSLT
builder, then actually applied with lxml to a sitemap document.

Proves the whole chain: the grammar emits a well-formed XSLT 1.0
stylesheet (namespaced ``xsl:*`` instructions interleaved with literal
HTML result elements), and a real XSLT processor transforms a sitemap
into the expected HTML — including resolving the ``{loc}``
attribute-value-template at runtime.
"""
from __future__ import annotations

from lxml import etree

from genro_builders.builder import BuilderHandler
from genro_builders.contrib.xslt import XsltBuilder
from genro_builders.xml.examples.sitemap import SitemapBuilder

XSL = "http://www.w3.org/1999/XSL/Transform"


class _SitemapToHtml(XsltBuilder):
    """Stylesheet: render a <urlset> as an HTML table of its URLs."""

    def main(self, root):
        ss = root.stylesheet(version="1.0", xmlns_xslt=XSL)
        ss.xslt_output(method="html", encoding="UTF-8", indent="yes")
        tpl = ss.xslt_template(match="/urlset")
        html = tpl.html()
        html.head().title("Sitemap")
        body = html.body()
        body.h1("Sitemap")
        table = body.table()
        head_row = table.thead().tr()
        head_row.th("URL")
        head_row.th("Last modified")
        head_row.th("Priority")
        loop = table.tbody().for_each(select="url")
        row = loop.tr()
        row.td().a(href="{loc}").value_of(select="loc")
        row.td().value_of(select="lastmod")
        row.td().value_of(select="priority")


class _Sitemap(SitemapBuilder):
    """A small sitemap document used as transform input."""

    def main(self, root):
        s = root.urlset()
        a = s.url()
        a.loc("https://www.example.com/")
        a.lastmod("2026-06-01")
        b = s.url()
        b.loc("https://www.example.com/about")
        b.lastmod("2026-05-20")


def _stylesheet_str() -> str:
    sheet = _SitemapToHtml()
    BuilderHandler().add_builder(main=sheet)
    return sheet.render(target=False, doc_header=True)


def _sitemap_str() -> str:
    sm = _Sitemap()
    BuilderHandler().add_builder(main=sm)
    return sm.render(mode="xml", target=False, doc_header=True)


def test_stylesheet_markup_shape():
    out = _stylesheet_str()
    assert f'<xslt:stylesheet version="1.0" xmlns:xslt="{XSL}">' in out
    assert '<xslt:output method="html"' in out
    assert '<xslt:template match="/urlset">' in out
    assert '<xslt:for-each select="url">' in out
    assert '<a href="{loc}">' in out
    assert '<xslt:value-of select="loc">' in out


def test_stylesheet_well_formed():
    # Parsing as XML must not raise: the sheet is well-formed.
    etree.fromstring(_stylesheet_str().encode("utf-8"))


def test_xslt_transforms_sitemap():
    transform = etree.XSLT(etree.fromstring(_stylesheet_str().encode("utf-8")))
    result = transform(etree.fromstring(_sitemap_str().encode("utf-8")))
    html = str(result)

    assert "<h1>Sitemap</h1>" in html
    assert "<table>" in html
    # one anchor per <loc>, with the AVT {loc} resolved by the processor
    assert '<a href="https://www.example.com/">' in html
    assert '<a href="https://www.example.com/about">' in html
    assert html.count("<tr>") == 3  # header row + one per url
    assert "2026-06-01" in html
    assert "2026-05-20" in html
