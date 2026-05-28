# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for BuilderHandler.abs_datapath — P1 stage.

P1 covers the syntactic forms that do not require ancestor walk nor
symbolic dispatch:

    ``field``         — absolute, no-op
    ``^field``        — strip pointer mark
    ``volume:field``  — preserve volume prefix
    ``field?attr``    — preserve ?attr tail
    combinations of the above

Relative paths (``.x``) and symbolic scopes (``#...``) are expected to
raise NotImplementedError in P1 — P2 and P3 will land their behavior.

Test pattern: subclass HtmlBuilderHandler with main(self, root) that
seeds the tree; assert on the string returned by abs_datapath, never
on private helpers.
"""
from __future__ import annotations

import pytest

from genro_builders.contrib.html import HtmlBuilderHandler


class _Page(HtmlBuilderHandler):
    """Minimal handler that exposes a leaf node for path resolution."""

    def main(self, root) -> None:
        root.body(node_id="leaf")


def _leaf():
    """Return an instantiated handler and its leaf node."""
    page = _Page()
    page.create()
    return page, page.node_by_id("leaf")


# ---------------------------------------------------------------------------
# Absolute (no transformation)
# ---------------------------------------------------------------------------


def test_absolute_field_is_returned_as_is():
    page, leaf = _leaf()
    assert page.abs_datapath(leaf, "field") == "field"


def test_absolute_dotted_path_is_returned_as_is():
    page, leaf = _leaf()
    assert page.abs_datapath(leaf, "user.name") == "user.name"


# ---------------------------------------------------------------------------
# Pointer mark (^) stripping
# ---------------------------------------------------------------------------


def test_pointer_mark_is_stripped():
    page, leaf = _leaf()
    assert page.abs_datapath(leaf, "^field") == "field"


def test_pointer_mark_stripped_on_dotted_path():
    page, leaf = _leaf()
    assert page.abs_datapath(leaf, "^user.name") == "user.name"


# ---------------------------------------------------------------------------
# Volume prefix preserved
# ---------------------------------------------------------------------------


def test_volume_prefix_preserved():
    page, leaf = _leaf()
    assert page.abs_datapath(leaf, "vol:field") == "vol:field"


def test_volume_prefix_preserved_with_pointer_mark():
    page, leaf = _leaf()
    assert page.abs_datapath(leaf, "^vol:field") == "vol:field"


def test_volume_prefix_preserved_on_dotted_path():
    page, leaf = _leaf()
    assert page.abs_datapath(leaf, "vol:user.name") == "vol:user.name"


# ---------------------------------------------------------------------------
# ?attr tail preserved
# ---------------------------------------------------------------------------


def test_attr_tail_preserved():
    page, leaf = _leaf()
    assert page.abs_datapath(leaf, "field?color") == "field?color"


def test_attr_tail_preserved_with_pointer_mark():
    page, leaf = _leaf()
    assert page.abs_datapath(leaf, "^field?color") == "field?color"


def test_volume_and_attr_combined():
    page, leaf = _leaf()
    assert page.abs_datapath(leaf, "vol:field?color") == "vol:field?color"


def test_pointer_volume_and_attr_combined():
    page, leaf = _leaf()
    assert page.abs_datapath(leaf, "^vol:user.name?size") == "vol:user.name?size"


# ---------------------------------------------------------------------------
# Forms reserved for later phases — explicit NotImplementedError (no fallback)
# ---------------------------------------------------------------------------


def test_relative_path_raises_not_implemented_in_p1():
    page, leaf = _leaf()
    with pytest.raises(NotImplementedError):
        page.abs_datapath(leaf, ".name")


def test_symbolic_scope_raises_not_implemented_in_p1():
    page, leaf = _leaf()
    with pytest.raises(NotImplementedError):
        page.abs_datapath(leaf, "#FORM.name")
