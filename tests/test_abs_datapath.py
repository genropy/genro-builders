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
# Relative paths — ancestor walk (P2)
# ---------------------------------------------------------------------------


class _PageWithDatapath(HtmlBuilderHandler):
    """body has datapath='myform'; the leaf is a child of body."""

    def main(self, root) -> None:
        body = root.body(datapath="myform")
        body.div(node_id="leaf")


def test_relative_resolves_via_ancestor_datapath():
    page = _PageWithDatapath()
    page.create()
    leaf = page.node_by_id("leaf")
    assert page.abs_datapath(leaf, ".name") == "myform.name"


def test_relative_with_attr_tail_preserved():
    page = _PageWithDatapath()
    page.create()
    leaf = page.node_by_id("leaf")
    assert page.abs_datapath(leaf, ".name?color") == "myform.name?color"


def test_relative_with_pointer_mark():
    page = _PageWithDatapath()
    page.create()
    leaf = page.node_by_id("leaf")
    assert page.abs_datapath(leaf, "^.name") == "myform.name"


class _PageRelativeChain(HtmlBuilderHandler):
    """Chain of datapaths: grandparent absolute, parent relative.

    The walk consumes the parent's '.row' (still relative) then prepends
    the grandparent's 'form' (absolute) and stops.
    """

    def main(self, root) -> None:
        outer = root.body(datapath="form")
        inner = outer.div(datapath=".row")
        inner.span(node_id="leaf")


def test_relative_chains_through_relative_ancestor_datapath():
    page = _PageRelativeChain()
    page.create()
    leaf = page.node_by_id("leaf")
    assert page.abs_datapath(leaf, ".name") == "form.row.name"


class _PageNoDatapathAnchor(HtmlBuilderHandler):
    """No ancestor carries a datapath."""

    def main(self, root) -> None:
        root.body().div(node_id="leaf")


def test_relative_without_anchor_raises_value_error():
    page = _PageNoDatapathAnchor()
    page.create()
    leaf = page.node_by_id("leaf")
    with pytest.raises(ValueError):
        page.abs_datapath(leaf, ".name")


def test_relative_walk_uses_leaf_datapath_too():
    """If the leaf itself carries an absolute datapath, no ancestor is
    consulted: the walk starts from ``node`` (current = node)."""

    class P(HtmlBuilderHandler):
        def main(self, root) -> None:
            root.body().div(node_id="leaf", datapath="own")

    page = P()
    page.create()
    leaf = page.node_by_id("leaf")
    assert page.abs_datapath(leaf, ".name") == "own.name"


# ---------------------------------------------------------------------------
# Forms reserved for later phases — explicit NotImplementedError (no fallback)
# ---------------------------------------------------------------------------


def test_symbolic_scope_raises_not_implemented_in_p2():
    page, leaf = _leaf()
    with pytest.raises(NotImplementedError):
        page.abs_datapath(leaf, "#FORM.name")


def test_callable_ancestor_datapath_raises_not_implemented():
    """P4: callable datapath on an ancestor is recognized but not implemented."""

    class P(HtmlBuilderHandler):
        def main(self, root) -> None:
            root.body(datapath=lambda: "x").div(node_id="leaf")

    page = P()
    page.create()
    leaf = page.node_by_id("leaf")
    with pytest.raises(NotImplementedError):
        page.abs_datapath(leaf, ".name")


def test_pointer_ancestor_datapath_raises_not_implemented():
    """P4: an ancestor datapath that is itself a ^pointer is deferred."""

    class P(HtmlBuilderHandler):
        def main(self, root) -> None:
            root.body(datapath="^src").div(node_id="leaf")

    page = P()
    page.create()
    leaf = page.node_by_id("leaf")
    with pytest.raises(NotImplementedError):
        page.abs_datapath(leaf, ".name")


def test_symbolic_ancestor_datapath_raises_not_implemented():
    """P4: an ancestor datapath that is itself #symbolic is deferred."""

    class P(HtmlBuilderHandler):
        def main(self, root) -> None:
            root.body(datapath="#FORM").div(node_id="leaf")

    page = P()
    page.create()
    leaf = page.node_by_id("leaf")
    with pytest.raises(NotImplementedError):
        page.abs_datapath(leaf, ".name")
