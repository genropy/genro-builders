# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for the BagBuilderBase class-level builder registry.

Concrete dialects declare a canonical ``_name`` attribute and are
auto-registered at class definition. Lookup happens via
:meth:`BagBuilderBase.get_builder_class`.

Note: ``MarkdownBuilder`` is dormant during the 2026-05 restart
(its ``__init__`` raises ``ImportError``), so it is not covered here.
The ``_name = "markdown"`` annotation on the class is harmless and
will activate automatically when the module is reactivated.
"""
from __future__ import annotations

import pytest

from genro_builders import BagBuilderBase
from genro_builders.contrib.data import DataBuilder
from genro_builders.contrib.html import HtmlBuilder
from genro_builders.contrib.svg import SvgBuilder


def test_html_builder_is_registered():
    assert BagBuilderBase.get_builder_class("html") is HtmlBuilder


def test_svg_builder_is_registered():
    assert BagBuilderBase.get_builder_class("svg") is SvgBuilder


def test_data_builder_is_registered():
    assert BagBuilderBase.get_builder_class("data") is DataBuilder


def test_real_builders_have_explicit_name():
    """Each public dialect declares ``_name`` as a class attribute."""
    assert HtmlBuilder._name == "html"
    assert SvgBuilder._name == "svg"
    assert DataBuilder._name == "data"


def test_lookup_unknown_name_raises_lookup_error():
    with pytest.raises(LookupError) as excinfo:
        BagBuilderBase.get_builder_class("does-not-exist")
    assert "does-not-exist" in str(excinfo.value)


def test_base_class_does_not_register_itself():
    """``BagBuilderBase`` is abstract: it must not appear in the registry."""
    for cls in BagBuilderBase._registry.values():
        assert cls is not BagBuilderBase
