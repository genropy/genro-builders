# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""End-to-end test for the phase-1 XSLT->Python transpiler.

The round-trip proves the chain ``.xslt -> Python -> execute -> render``
reproduces the original stylesheet. Equivalence is *structural* (same
element tree, ignoring the insignificant whitespace the original was
pretty-printed with), not byte-identity — the regenerated sheet is not
re-indented, so a raw c14n would differ only on blank text.

A second check runs the regenerated sheet through a real lxml XSLT
processor against a sitemap, so the round-trip is not merely
syntactic: the rebuilt stylesheet still transforms.
"""
from __future__ import annotations

from pathlib import Path

from lxml import etree

from genro_builders.builder import BuilderHandler
from genro_builders.contrib.xslt.transpiler import XsltTranspiler
from genro_builders.contrib.xslt.transpiler.__main__ import main

XSL = "http://www.w3.org/1999/XSL/Transform"
_EXAMPLE = (
    Path(__file__).parent.parent
    / "src/genro_builders/contrib/xslt/examples"
    / "01_sitemap_to_html/01_sitemap_to_html.xslt"
)

_SITEMAP = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<urlset xmlns="">'
    "<url><loc>https://www.example.com/</loc><lastmod>2026-06-01</lastmod>"
    "<priority>0.8</priority></url>"
    "<url><loc>https://www.example.com/about</loc><lastmod>2026-05-20</lastmod>"
    "<priority>0.5</priority></url>"
    "</urlset>"
)


def _canon(xml_text: str) -> bytes:
    """Canonical form ignoring insignificant inter-element whitespace."""
    parser = etree.XMLParser(remove_blank_text=True)
    return etree.tostring(etree.fromstring(xml_text.encode(), parser), method="c14n")


def _regenerate(xslt_source: str) -> str:
    """Transpile, execute the generated module, render the stylesheet."""
    code = XsltTranspiler(handler_name="RoundTrip").transpile(xslt_source)
    namespace: dict[str, object] = {}
    exec(code, namespace)  # noqa: S102 - executing our own generated code
    page = namespace["RoundTrip"]()
    BuilderHandler().add_builder(page)
    return page.render(target=False, doc_header=True)


def test_round_trip_is_structurally_identical():
    original = _EXAMPLE.read_text(encoding="utf-8")
    regenerated = _regenerate(original)
    assert _canon(regenerated) == _canon(original)


def test_regenerated_sheet_still_transforms():
    original = _EXAMPLE.read_text(encoding="utf-8")
    regenerated = _regenerate(original)
    transform = etree.XSLT(etree.fromstring(regenerated.encode("utf-8")))
    html = str(transform(etree.fromstring(_SITEMAP.encode("utf-8"))))
    assert "<h1>Sitemap</h1>" in html
    assert '<a href="https://www.example.com/">' in html
    assert '<a href="https://www.example.com/about">' in html
    assert html.count("<tr>") == 3  # header row + one per url


def test_cli_writes_output_file(tmp_path):
    out = tmp_path / "generated.py"
    rc = main(["--xslt", str(_EXAMPLE), "--handler-name", "Sitemap", "--output", str(out)])
    assert rc == 0
    code = out.read_text(encoding="utf-8")
    assert "class Sitemap(XsltBuilder):" in code
    # the generated module executes and rebuilds an equivalent sheet
    namespace: dict[str, object] = {}
    exec(code, namespace)  # noqa: S102
    page = namespace["Sitemap"]()
    BuilderHandler().add_builder(page)
    regenerated = page.render(target=False, doc_header=True)
    assert _canon(regenerated) == _canon(_EXAMPLE.read_text(encoding="utf-8"))
