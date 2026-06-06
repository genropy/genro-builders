# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for the BuilderBase class-level builder registry.

Concrete dialects declare a canonical ``_name`` attribute and are
auto-registered at class definition. Lookup happens via
:meth:`BuilderBase.get_builder_class`.

Note: ``MarkdownBuilder`` is dormant during the 2026-05 restart
(its ``__init__`` raises ``ImportError``), so it is not covered here.
The ``_name = "markdown"`` annotation on the class is harmless and
will activate automatically when the module is reactivated.
"""
from __future__ import annotations

import pytest

from genro_builders import BuilderBase
from genro_builders.contrib.html import HtmlBuilder
from genro_builders.contrib.svg import SvgBuilder
from genro_builders.data import DataBuilderBase


def test_html_builder_is_registered():
    assert BuilderBase.get_builder_class("html") is HtmlBuilder


def test_svg_builder_is_registered():
    assert BuilderBase.get_builder_class("svg") is SvgBuilder


def test_data_base_is_not_registered():
    """``DataBuilderBase`` is a base (``_name = None``): never registered."""
    assert DataBuilderBase._name is None
    for cls in BuilderBase._registry.values():
        assert cls is not DataBuilderBase


def test_real_builders_have_explicit_name():
    """Each public dialect declares ``_name`` as a class attribute."""
    assert HtmlBuilder._name == "html"
    assert SvgBuilder._name == "svg"


def test_lookup_unknown_name_raises_lookup_error():
    with pytest.raises(LookupError) as excinfo:
        BuilderBase.get_builder_class("does-not-exist")
    assert "does-not-exist" in str(excinfo.value)


def test_base_class_does_not_register_itself():
    """``BuilderBase`` is abstract: it must not appear in the registry."""
    for cls in BuilderBase._registry.values():
        assert cls is not BuilderBase
