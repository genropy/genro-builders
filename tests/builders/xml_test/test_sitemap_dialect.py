# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for the Sitemap example dialect.

A small generated XSD dialect: nested ``urlset``/``url``, an enumerated
``changefreq``, and a bounded ``priority``. The generated module is pure
Python; the regeneration round-trip is gated on ``xmlschema``.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from genro_builders.xml.examples.sitemap import (
    SitemapBuilder,
    SitemapHandler,
)

_SITEMAP_DIR = (
    Path(__file__).resolve().parents[2]
    / "../src/genro_builders/xml/examples/sitemap"
).resolve()
SITEMAP_XSD = _SITEMAP_DIR / "sitemap.xsd"
SITEMAP_GENERATED = _SITEMAP_DIR / "sitemap.py"

_MODULE_DOCSTRING = (
    "XML Sitemap dialect, generated from sitemap.xsd (modelled on the "
    "public Sitemaps protocol 0.9). A small real-world XSD example: nested "
    "urlset/url, enumerated changefreq, bounded priority."
)


def test_builder_schema_contains_known_elements():
    builder = SitemapBuilder()
    schema_tags = set(builder._schema_tag_names)
    assert {"urlset", "url", "loc", "changefreq", "priority"}.issubset(schema_tags)


def test_handler_renders_a_sitemap_document():
    class MySitemap(SitemapHandler):
        def main(self, root):
            s = root.urlset()
            home = s.url()
            home.loc("https://www.example.com/")
            home.changefreq("daily")
            home.priority(Decimal("1.0"))

    h = MySitemap()
    h.create()
    xml = h.render(mode="xml", target=False)
    assert xml == (
        "<urlset><url>"
        "<loc>https://www.example.com/</loc>"
        "<changefreq>daily</changefreq>"
        "<priority>1.0</priority>"
        "</url></urlset>"
    )


def test_pretty_render_is_multiline():
    class MySitemap(SitemapHandler):
        def main(self, root):
            root.urlset().url().loc("https://x/")

    h = MySitemap()
    h.create()
    pretty = h.render(mode="xml", pretty=True, target=False)
    assert "\n" in pretty
    assert pretty.startswith("<urlset>")


def test_regeneration_is_byte_identical():
    """Re-running the codegen on the committed XSD reproduces the
    committed module byte-for-byte."""
    pytest.importorskip("xmlschema")

    from genro_builders.xml.transpiler import (
        PythonGenerator,
        XmlschemaBackend,
    )

    model = XmlschemaBackend().load(SITEMAP_XSD)
    source = PythonGenerator().render(
        model,
        dialect_name="Sitemap",
        module_docstring=_MODULE_DOCSTRING,
    )
    committed = SITEMAP_GENERATED.read_text(encoding="utf-8")
    assert source == committed, (
        "Codegen output drifted from the committed file. Regenerate with: "
        f"python -m genro_builders.xml.transpiler --xsd {SITEMAP_XSD} "
        f"--dialect-name Sitemap --output {SITEMAP_GENERATED}"
    )
