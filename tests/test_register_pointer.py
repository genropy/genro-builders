# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for BuilderHandler.register_pointer and the self.pointer_map state.

Covers Phase 1 (isolated behavior): registering / unregistering pointer
dependencies built into the source via the canonical builder API.

Map key rule (DAT.2):
    pointer on node.value    -> abs_datapath(node, pointer)
    pointer on node.attr[a]  -> abs_datapath(node, pointer) + "?" + a

Map value:
    dict {id(node): node} — BuilderBagNode is not hashable.

Tests build pointers ONLY via the canonical builder API (kwargs on the
@element call inside main(self, root)), never by writing to node.attr or
node.value directly — that would bypass the bag's subscribe pipeline and
test an unreachable state.
"""
from __future__ import annotations

import pytest

from genro_builders.contrib.html import HtmlBuilderHandler

# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------


def test_pointer_map_starts_empty():
    """A freshly created handler has an empty pointer_map."""

    class P(HtmlBuilderHandler):
        def main(self, root) -> None:
            root.body()

    page = P()
    page.create()
    assert page.pointer_map == {}


# ---------------------------------------------------------------------------
# Registration — pointer on an attribute
# ---------------------------------------------------------------------------


def test_register_pointer_on_attribute():
    """A pointer set as kwarg becomes pointer_map[path?attrname] -> node."""

    class P(HtmlBuilderHandler):
        def main(self, root) -> None:
            body = root.body(datapath="myform")
            body.div(color="^.color", node_id="leaf")

    page = P()
    page.create()
    page.register_pointer(page.source.node(0))
    leaf = page.node_by_id("leaf")
    assert "myform.color?color" in page.pointer_map
    assert id(leaf) in page.pointer_map["myform.color?color"]
    assert page.pointer_map["myform.color?color"][id(leaf)] is leaf


def test_register_multiple_attribute_pointers_on_same_node():
    """Two pointer attributes on the same node produce two distinct keys."""

    class P(HtmlBuilderHandler):
        def main(self, root) -> None:
            body = root.body(datapath="myform")
            body.div(color="^.color", style="^.style", node_id="leaf")

    page = P()
    page.create()
    page.register_pointer(page.source.node(0))
    leaf = page.node_by_id("leaf")
    assert page.pointer_map["myform.color?color"][id(leaf)] is leaf
    assert page.pointer_map["myform.style?style"][id(leaf)] is leaf


def test_register_two_nodes_share_one_path():
    """Two distinct nodes pointing to the same path land under the same key."""

    class P(HtmlBuilderHandler):
        def main(self, root) -> None:
            body = root.body(datapath="myform")
            body.div(color="^.color", node_id="leaf1")
            body.span(color="^.color", node_id="leaf2")

    page = P()
    page.create()
    page.register_pointer(page.source.node(0))
    leaf1 = page.node_by_id("leaf1")
    leaf2 = page.node_by_id("leaf2")
    inner = page.pointer_map["myform.color?color"]
    assert id(leaf1) in inner and inner[id(leaf1)] is leaf1
    assert id(leaf2) in inner and inner[id(leaf2)] is leaf2


# ---------------------------------------------------------------------------
# Registration — pointer carries its own ?attr (preserved by abs_datapath)
# ---------------------------------------------------------------------------


def test_register_pointer_raw_with_attr_suffix():
    """A pointer with its own ?attr keeps it in the path (key has both)."""

    class P(HtmlBuilderHandler):
        def main(self, root) -> None:
            body = root.body(datapath="myform")
            body.div(style="^.x?bold", node_id="leaf")

    page = P()
    page.create()
    page.register_pointer(page.source.node(0))
    leaf = page.node_by_id("leaf")
    # abs_datapath preserves the ?bold tail; register_pointer appends ?style
    # (the destination attribute name).
    assert page.pointer_map["myform.x?bold?style"][id(leaf)] is leaf


# ---------------------------------------------------------------------------
# Registration — subtree walk
# ---------------------------------------------------------------------------


def test_register_walks_the_subtree():
    """Pointers on nested descendants are picked up by a single root call."""

    class P(HtmlBuilderHandler):
        def main(self, root) -> None:
            body = root.body(datapath="myform")
            outer = body.div(color="^.outer_color", node_id="outer")
            outer.span(color="^.inner_color", node_id="inner")

    page = P()
    page.create()
    page.register_pointer(page.source.node(0))
    outer = page.node_by_id("outer")
    inner = page.node_by_id("inner")
    assert page.pointer_map["myform.outer_color?color"][id(outer)] is outer
    assert page.pointer_map["myform.inner_color?color"][id(inner)] is inner


def test_register_node_without_pointers_is_noop():
    """A subtree carrying no ^... strings leaves pointer_map empty."""

    class P(HtmlBuilderHandler):
        def main(self, root) -> None:
            body = root.body()
            body.div(node_id="leaf")

    page = P()
    page.create()
    page.register_pointer(page.source.node(0))
    assert page.pointer_map == {}


# ---------------------------------------------------------------------------
# Errors from abs_datapath propagate
# ---------------------------------------------------------------------------


def test_register_propagates_value_error_for_relative_without_anchor():
    """A relative pointer with no datapath in the ancestor chain raises.

    The error surfaces during ``create()`` itself, because ``create``
    invokes ``register_pointer`` on the populated subtree.
    """

    class P(HtmlBuilderHandler):
        def main(self, root) -> None:
            # No datapath anywhere — the relative pointer can't resolve.
            body = root.body()
            body.div(color="^.color", node_id="leaf")

    page = P()
    with pytest.raises(ValueError):
        page.create()


# ---------------------------------------------------------------------------
# Unregistration — round-trip and partial
# ---------------------------------------------------------------------------


def test_unregister_round_trip_clears_the_map():
    """register + unregister of the same subtree leaves pointer_map empty."""

    class P(HtmlBuilderHandler):
        def main(self, root) -> None:
            body = root.body(datapath="myform")
            body.div(color="^.color", node_id="leaf")

    page = P()
    page.create()
    root_node = page.source.node(0)
    page.register_pointer(root_node)
    assert page.pointer_map  # non-empty
    page.register_pointer(root_node, unregister=True)
    assert page.pointer_map == {}


def test_unregister_prunes_empty_path_entries():
    """Removing the last node under a path removes the key entirely."""

    class P(HtmlBuilderHandler):
        def main(self, root) -> None:
            body = root.body(datapath="myform")
            body.div(color="^.color", node_id="leaf")

    page = P()
    page.create()
    root_node = page.source.node(0)
    page.register_pointer(root_node)
    page.register_pointer(root_node, unregister=True)
    # The "myform.color?color" key must be gone, not left as an empty dict.
    assert "myform.color?color" not in page.pointer_map


def test_unregister_unknown_path_is_silent():
    """Unregistering a subtree that was never registered raises nothing."""

    class P(HtmlBuilderHandler):
        def main(self, root) -> None:
            body = root.body(datapath="myform")
            body.div(color="^.color", node_id="leaf")

    page = P()
    page.create()
    # No prior register_pointer call.
    page.register_pointer(page.source.node(0), unregister=True)
    assert page.pointer_map == {}
