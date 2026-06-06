# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Hierarchy + registration tests for the XSLT dialect.

Verifies that the XSLT builder sits on the shared XML base, that the
dialect is registered under ``xslt``, that it renders via the core
``XmlRenderer``, and that its grammar rejects unknown elements.
"""
from __future__ import annotations

import pytest

from genro_builders.builder import BagBuilderBase
from genro_builders.contrib.xslt import XsltBuilder, XsltBuilderHandler
from genro_builders.xml import XmlBuilderBase


def test_xslt_builder_is_xml_base():
    assert issubclass(XsltBuilder, XmlBuilderBase)
    assert XsltBuilder._default_render_mode == "xml"


def test_xslt_registered():
    assert BagBuilderBase.get_builder_class("xslt") is XsltBuilder


def test_renderer_is_xmlrenderer():
    class _S(XsltBuilderHandler):
        def main(self, root):
            root.stylesheet()

    h = _S()
    h.create()
    renderer = h._get_renderer("xml")
    assert type(renderer).__name__ == "XmlRenderer"


def test_grammar_rejects_unknown_element():
    class _S(XsltBuilderHandler):
        def main(self, root):
            root.stylesheet().foobar()

    h = _S()
    with pytest.raises(AttributeError):
        h.create()
