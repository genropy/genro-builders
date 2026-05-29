# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for BuilderHandler.abs_datapath.

Covers all supported path forms:

    ``field``           — absolute, no-op
    ``^field``          — strip pointer mark
    ``volume:field``    — preserve volume prefix
    ``field?attr``      — preserve ?attr tail
    ``.x``              — relative: walk ancestor datapath chain
    ``a.#parent.b``     — #parent collapses preceding segment
    ``#FORM.x``         — nearest ancestor with formId or form=True
    ``#ANCHOR.x``       — nearest ancestor with attr _anchor present
    ``#<node_id>.x``    — node carrying that node_id

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
# Eager pointer mark (=) stripping — symmetric to ^ (DB-D9)
# ---------------------------------------------------------------------------


def test_equals_mark_is_stripped():
    page, leaf = _leaf()
    assert page.abs_datapath(leaf, "=field") == "field"


def test_equals_mark_stripped_on_dotted_path():
    page, leaf = _leaf()
    assert page.abs_datapath(leaf, "=user.name") == "user.name"


def test_equals_mark_with_volume():
    page, leaf = _leaf()
    assert page.abs_datapath(leaf, "=vol:field") == "vol:field"


def test_equals_mark_with_attr_tail():
    page, leaf = _leaf()
    assert page.abs_datapath(leaf, "=field?color") == "field?color"


def test_equals_mark_volume_and_attr_combined():
    page, leaf = _leaf()
    assert page.abs_datapath(leaf, "=vol:user.name?size") == "vol:user.name?size"


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


def test_relative_with_equals_mark():
    page = _PageWithDatapath()
    page.create()
    leaf = page.node_by_id("leaf")
    assert page.abs_datapath(leaf, "=.name") == "myform.name"


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
# #parent path-level rewrite (filesystem ".." equivalent)
# ---------------------------------------------------------------------------


def test_parent_collapses_preceding_segment():
    page, leaf = _leaf()
    assert page.abs_datapath(leaf, "a.b.#parent.c") == "a.c"


def test_parent_collapses_multiple_segments():
    page, leaf = _leaf()
    assert page.abs_datapath(leaf, "a.b.c.#parent.#parent.d") == "a.d"


def test_parent_after_relative_resolution():
    """#parent applies AFTER the ancestor walk has composed the path."""
    page = _PageWithDatapath()       # body.datapath="myform"
    page.create()
    leaf = page.node_by_id("leaf")
    # relative resolves to "myform.row.name", then #parent collapses "row"
    assert page.abs_datapath(leaf, ".row.#parent.name") == "myform.name"


def test_parent_with_volume_and_attr():
    page, leaf = _leaf()
    assert page.abs_datapath(leaf, "vol:a.b.#parent.c?color") == "vol:a.c?color"


def test_parent_with_nothing_to_cancel_raises():
    """No silent drop: too many #parent segments raises ValueError."""
    page, leaf = _leaf()
    with pytest.raises(ValueError):
        page.abs_datapath(leaf, "a.#parent.#parent.b")


# ---------------------------------------------------------------------------
# Symbolic scopes (P3): #FORM, #ANCHOR, #nodeId
# ---------------------------------------------------------------------------


def test_symbolic_form_with_formId():
    """#FORM resolves to the nearest ancestor with attr formId set."""

    class P(HtmlBuilderHandler):
        def main(self, root) -> None:
            root.body(formId="inv", datapath="f").div(node_id="leaf")

    page = P()
    page.create()
    leaf = page.node_by_id("leaf")
    assert page.abs_datapath(leaf, "#FORM.x") == "f.x"


def test_symbolic_form_with_form_true():
    """#FORM also matches form=True (DB-D3, replaces legacy _fakeform)."""

    class P(HtmlBuilderHandler):
        def main(self, root) -> None:
            root.body(form=True, datapath="f").div(node_id="leaf")

    page = P()
    page.create()
    leaf = page.node_by_id("leaf")
    assert page.abs_datapath(leaf, "#FORM.x") == "f.x"


def test_symbolic_form_walks_past_unmarked_intermediate():
    """The walk continues past ancestors that are not marked."""

    class P(HtmlBuilderHandler):
        def main(self, root) -> None:
            outer = root.body(formId="inv", datapath="f")
            inner = outer.div()                  # unmarked intermediate
            inner.span(node_id="leaf")

    page = P()
    page.create()
    leaf = page.node_by_id("leaf")
    assert page.abs_datapath(leaf, "#FORM.x") == "f.x"


def test_symbolic_form_without_marked_ancestor_raises_key_error():
    class P(HtmlBuilderHandler):
        def main(self, root) -> None:
            root.body().div(node_id="leaf")

    page = P()
    page.create()
    leaf = page.node_by_id("leaf")
    with pytest.raises(KeyError):
        page.abs_datapath(leaf, "#FORM.x")


def test_symbolic_anchor_with_attribute_presence():
    """#ANCHOR matches the nearest ancestor with attr _anchor present."""

    class P(HtmlBuilderHandler):
        def main(self, root) -> None:
            root.body(_anchor="whatever", datapath="a").div(node_id="leaf")

    page = P()
    page.create()
    leaf = page.node_by_id("leaf")
    assert page.abs_datapath(leaf, "#ANCHOR.x") == "a.x"


def test_symbolic_anchor_value_is_arbitrary():
    """_anchor value is arbitrary: presence alone is the marker."""

    class P(HtmlBuilderHandler):
        def main(self, root) -> None:
            root.body(_anchor=True, datapath="a").div(node_id="leaf")

    page = P()
    page.create()
    leaf = page.node_by_id("leaf")
    assert page.abs_datapath(leaf, "#ANCHOR.x") == "a.x"


def test_symbolic_anchor_without_marker_raises_key_error():
    class P(HtmlBuilderHandler):
        def main(self, root) -> None:
            root.body().div(node_id="leaf")

    page = P()
    page.create()
    leaf = page.node_by_id("leaf")
    with pytest.raises(KeyError):
        page.abs_datapath(leaf, "#ANCHOR.x")


def test_symbolic_node_id_resolves_via_node_by_id():
    """#<id> dispatches to node_by_id and composes with the target's datapath."""

    class P(HtmlBuilderHandler):
        def main(self, root) -> None:
            root.body(node_id="hub", datapath="rec").div(node_id="leaf")

    page = P()
    page.create()
    leaf = page.node_by_id("leaf")
    assert page.abs_datapath(leaf, "#hub.x") == "rec.x"


def test_symbolic_unknown_id_raises_key_error():
    page, leaf = _leaf()
    with pytest.raises(KeyError):
        page.abs_datapath(leaf, "#totally-unknown.x")


def test_symbolic_with_pointer_mark():
    """^#FORM.x: pointer mark is stripped, symbolic dispatch happens after."""

    class P(HtmlBuilderHandler):
        def main(self, root) -> None:
            root.body(formId="inv", datapath="f").div(node_id="leaf")

    page = P()
    page.create()
    leaf = page.node_by_id("leaf")
    assert page.abs_datapath(leaf, "^#FORM.x") == "f.x"


