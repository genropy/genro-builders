# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""01 — Sitemap to HTML: write an XSLT 1.0 stylesheet pythonically.

What you learn:
    - An XSLT stylesheet is just XML, so it renders through the shared
      `XmlRenderer` — no XSLT-specific renderer exists.
    - Namespaced instructions (`xslt:value-of`, `xslt:for-each`) come from
      `@element(_meta={"render_tag": "xslt:..."})`: the Python method keeps
      a legal name (`value_of`), the emitted tag carries the prefix and
      hyphen (`xslt:value-of`).
    - The `xslt` prefix is declared as a plain attribute on the root:
      `stylesheet(xmlns_xslt=...)` surfaces as `xmlns:xslt="..."`.
    - HTML output tags are *literal result elements*: the whole HTML5
      vocabulary is mixed into the XSLT grammar (interleaved with the
      instructions), not a nested HTML sub-builder.
    - The stylesheet is then applied to a real sitemap with lxml; the
      `{loc}` attribute-value-template is resolved by the XSLT processor.

Prerequisites: None for the XSLT dialect; familiarity with the sitemap
XSD example helps (it supplies the input document here).

Usage:
    python 01_sitemap_to_html.py
"""
from __future__ import annotations

from pathlib import Path

from lxml import etree

from genro_builders.contrib.xslt import XsltBuilder
from genro_builders.xml.examples.sitemap import SitemapBuilder

XSL = "http://www.w3.org/1999/XSL/Transform"


class SitemapToHtml(XsltBuilder):
    """A stylesheet that renders a <urlset> as an HTML table of URLs."""

    def main(self, root):
        ss = root.stylesheet(version="1.0", xmlns_xslt=XSL)
        ss.xslt_output(method="html", encoding="UTF-8", indent="yes")

        tpl = ss.xslt_template(match="/urlset")
        html = tpl.html()
        html.head().title("Sitemap")
        body = html.body()
        body.h1("Sitemap")

        table = body.table()
        header = table.thead().tr()
        header.th("URL")
        header.th("Last modified")
        header.th("Priority")

        loop = table.tbody().for_each(select="url")
        row = loop.tr()
        row.td().a(href="{loc}").value_of(select="loc")
        row.td().value_of(select="lastmod")
        row.td().value_of(select="priority")


class SampleSitemap(SitemapBuilder):
    """A small sitemap used as the transform input."""

    def main(self, root):
        urlset = root.urlset()
        home = urlset.url()
        home.loc("https://www.example.com/")
        home.lastmod("2026-06-01")
        about = urlset.url()
        about.loc("https://www.example.com/about")
        about.lastmod("2026-05-20")


if __name__ == "__main__":
    # 1. Build the stylesheet and render it (XML output, doc header on).
    sheet = SitemapToHtml()
    sheet.create()
    stylesheet_xml = sheet.render(target=False, doc_header=True, pretty=True)

    output_xslt = Path("01_sitemap_to_html.xslt")
    output_xslt.write_text(stylesheet_xml)
    print(stylesheet_xml)

    # 2. Build a sample sitemap document.
    sm = SampleSitemap()
    sm.create()
    sitemap_xml = sm.render(mode="xml", target=False, doc_header=True)

    # 3. Apply the stylesheet to the sitemap with lxml — the real XSLT
    #    processor resolves the `{loc}` attribute-value-template.
    transform = etree.XSLT(etree.fromstring(stylesheet_xml.encode("utf-8")))
    result_html = str(transform(etree.fromstring(sitemap_xml.encode("utf-8"))))

    output_html = Path("01_sitemap_to_html.html")
    output_html.write_text(result_html)
    print("\n--- transformed HTML ---\n")
    print(result_html)
    print(f"\nSaved stylesheet to {output_xslt}")
    print(f"Saved HTML to {output_html}")
