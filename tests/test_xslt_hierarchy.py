# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Hierarchy + registration tests for the XSLT dialect.

Verifies that the XSLT builder sits on the shared XML base, that the
dialect is registered under ``xslt``, that it renders via the core
``XmlRenderer``, and that its grammar rejects unknown elements.
"""
from __future__ import annotations

import pytest

from genro_builders.builder import BuilderBase, BuilderHandler
from genro_builders.contrib.xslt import XsltBuilder
from genro_builders.xml import XmlBuilderBase


def test_xslt_builder_is_xml_base():
    assert issubclass(XsltBuilder, XmlBuilderBase)
    assert XsltBuilder._default_render_mode == "xml"


def test_xslt_registered():
    assert BuilderBase.get_builder_class("xslt") is XsltBuilder


def test_renderer_is_xmlrenderer():
    class _S(XsltBuilder):
        def main(self, root):
            root.stylesheet()

    page = _S()
    BuilderHandler().add_builder(page)
    assert type(page.renderer_xml).__name__ == "XmlRenderer"


def test_grammar_rejects_unknown_element():
    class _S(XsltBuilder):
        def main(self, root):
            root.stylesheet().foobar()

    page = _S()
    with pytest.raises(AttributeError):
        BuilderHandler().add_builder(page)
