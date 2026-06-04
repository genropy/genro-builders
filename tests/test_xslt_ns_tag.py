# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Unit tests for the XSLT namespace-tag mechanism (via ``render_tag``).

A grammar element may declare in its ``_meta`` a ``render_tag`` carrying
a namespace prefix (``xsl:value-of``); the shared ``XmlRenderer`` then
emits that tag instead of the bare Python method name. The namespace
itself is declared once on the root as an ``xmlns_<prefix>`` attribute,
which surfaces as ``xmlns:<prefix>``.

These tests exercise the renderer in isolation through a minimal inline
builder, so they do not depend on the XSLT dialect (built later). The
output type is XML (``XmlRenderer`` via ``renderer_xml``).
"""
from __future__ import annotations

from genro_builders.builder import BagBuilderBase, element
from genro_builders.builder_handler import BuilderHandler

XSL_URI = "http://www.w3.org/1999/XSL/Transform"


class _NsBuilder(BagBuilderBase):
    """Minimal builder: a root container plus two ``xsl:*`` elements and
    one plain (literal) element with no namespace."""

    _name = "_nstest"
    _default_render_mode = "xml"

    @element(sub_tags="*", _meta={"render_tag": "xsl:stylesheet"})
    def stylesheet(self): ...

    @element(sub_tags="*", _meta={"render_tag": "xsl:for-each"})
    def for_each(self): ...

    @element(_meta={"render_tag": "xsl:value-of"})
    def value_of(self): ...

    @element(sub_tags="*")
    def table(self): ...

    @element()
    def a(self): ...


class _NsHandler(BuilderHandler):
    builder_class = _NsBuilder


def _render(main):
    """Build a one-off handler around ``main`` and return its XML string."""

    class _H(_NsHandler):
        pass

    _H.main = lambda self, root: main(root)
    h = _H()
    h.create()
    return h.render(target=False)


def test_ns_local_composes_prefixed_tag():
    """``value_of`` (ns=xsl, local=value-of) emits ``<xsl:value-of>``."""
    out = _render(lambda root: root.stylesheet(xmlns_xsl=XSL_URI).value_of(select="x"))
    assert "<xsl:value-of select=\"x\"></xsl:value-of>" in out


def test_local_with_hyphen():
    """An underscore method maps to a hyphenated local-name via ``local``."""
    out = _render(lambda root: root.stylesheet(xmlns_xsl=XSL_URI).for_each(select="url"))
    assert "<xsl:for-each select=\"url\">" in out
    assert "</xsl:for-each>" in out


def test_node_tag_stays_python_legal():
    """The node tag is the Python name; only the emitted markup is prefixed."""

    class _H(_NsHandler):
        def main(self, root):
            root.stylesheet(xmlns_xsl=XSL_URI).for_each(select="url")

    h = _H()
    h.create()
    sheet = next(iter(h.source))
    fe = next(iter(sheet.value))
    assert fe.node_tag == "for_each"
    assert "<xsl:for-each" in h.render(target=False)


def test_xmlns_attr_underscore_to_colon():
    """``xmlns_xsl`` author attribute surfaces as ``xmlns:xsl``."""
    out = _render(lambda root: root.stylesheet(version="1.0", xmlns_xsl=XSL_URI))
    assert f'xmlns:xsl="{XSL_URI}"' in out
    assert 'version="1.0"' in out


def test_avt_brace_verbatim():
    """A single-brace attribute-value-template is emitted verbatim
    (not a ``${...}`` template, not a ``^``/``=`` pointer)."""
    out = _render(lambda root: root.stylesheet(xmlns_xsl=XSL_URI).a(href="{loc}"))
    assert 'href="{loc}"' in out


def test_no_ns_no_prefix():
    """An element without ``ns`` is emitted with the bare tag."""
    out = _render(lambda root: root.stylesheet(xmlns_xsl=XSL_URI).table())
    assert "<table>" in out
    assert "<xsl:table" not in out


def test_prefixed_tag_independent_of_xmlns_declaration():
    """The ``render_tag`` prefix is fixed on the element; it is emitted
    whether or not the namespace is declared on the root (a missing
    ``xmlns:xsl`` is a malformed document, the user's responsibility)."""
    out = _render(lambda root: root.stylesheet().value_of(select="x"))
    assert "<xsl:value-of" in out
