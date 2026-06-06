# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for BuilderHandler.register_pointer and the self.pointer_map state.

Covers Phase 1 (isolated behavior): registering / unregistering pointer
dependencies built into the source via the canonical builder API.

Map key rule (DAT.2):
    pointer on node.value    -> abs_datapath(node, pointer)
    pointer on node.attr[a]  -> abs_datapath(node, pointer) + "?" + a

Map value:
    dict {id(node): node} — SourceBagNode is not hashable.

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


# ---------------------------------------------------------------------------
# Phase 2 — automatic mapkeep on post-create source mutations
#
# After create() the source subscribes are active; the internal dispatcher
# _on_source_event maintains pointer_map coherent across ins/del events
# (structural, not user-facing). These tests verify the end-to-end behavior
# via the canonical API.
# ---------------------------------------------------------------------------


class PageTester(HtmlBuilderHandler):
    """Live handler for the mapkeep phase-2 walkthrough.

    Each ``test_NN_*`` method performs one canonical mutation and asserts
    the expected cumulative ``pointer_map`` state. The numeric prefix
    pins execution order (``dir()`` is alphabetical). New steps can be
    added as further numbered methods; the driver below picks them up
    automatically.
    """

    def main(self, root) -> None:
        """Initial source: a single ``body`` anchored at ``myform``."""
        root.body(datapath="myform", node_id="body")

    def test_01_simple_node(self) -> None:
        """A node with no pointers leaves ``pointer_map`` untouched."""
        body = self.node_by_id("body")
        body.div()
        assert self.pointer_map == {}

    def test_02_value_pointer(self) -> None:
        """A node whose ``value`` is a pointer registers under that path."""
        body = self.node_by_id("body")
        child = body.div("^.title")
        assert self.pointer_map["myform.title"] == {id(child): child}

    def test_03_attr_pointer(self) -> None:
        """A node carrying a pointer on an attribute registers under attr-keyed path."""
        body = self.node_by_id("body")
        child = body.div(color="^.color")
        assert self.pointer_map["myform.color?color"] == {id(child): child}

    def test_04_ins_subtree_with_mixed_pointers(self) -> None:
        """An ``ins`` of a pre-built subtree (plain + pointer-bearing children)
        registers only the pointer-bearing ones in ``pointer_map``.
        """
        new_root = self.new_root()
        mybox = new_root.div(datapath="row")
        mybox.div("Static title")
        p = mybox.div("^.text")
        body = self.node_by_id("body").value
        child = self.builder.set_child(
            body, mybox.node_tag, mybox.value, **dict(mybox.attr),
        )
        assert child.node_tag == "div"
        assert child.attr["datapath"] == "row"
        assert [n.node_tag for n in child.value.nodes] == ["div", "div"]
        assert self.pointer_map["row.text"] == {id(p): p}

    def test_05_del_simple_node(self) -> None:
        """Removing a node with no pointers leaves ``pointer_map`` unchanged."""
        body = self.node_by_id("body").value
        before = dict(self.pointer_map)
        body.pop_node("div_0")
        assert self.pointer_map == before
        assert body.node("div_0") is None

    def test_06_del_value_pointer(self) -> None:
        """Removing the node with a value pointer drops its entry from ``pointer_map``."""
        body = self.node_by_id("body").value
        body.pop_node("div_1")
        assert "myform.title" not in self.pointer_map
        assert body.node("div_1") is None

    def test_07_del_attr_pointer(self) -> None:
        """Removing the node with an attr pointer drops its entry from ``pointer_map``."""
        body = self.node_by_id("body").value
        body.pop_node("div_2")
        assert "myform.color?color" not in self.pointer_map
        assert body.node("div_2") is None

    def test_08_del_subtree(self) -> None:
        """Removing the wrapper subtree drops all its nested pointers from ``pointer_map``."""
        body = self.node_by_id("body").value
        body.pop_node("div_3")
        assert "row.text" not in self.pointer_map
        assert body.node("div_3") is None

    def test_09_upd_value_scalar_to_scalar(self) -> None:
        """value scalar → scalar: ``pointer_map`` unchanged."""
        body = self.node_by_id("body")
        target = body.div("first", node_id="upd_09")
        before = dict(self.pointer_map)
        target.set_value("second")
        assert self.pointer_map == before

    def test_10_upd_value_scalar_to_pointer(self) -> None:
        """value scalar → pointer: a new entry is registered for ``node``."""
        body = self.node_by_id("body")
        target = body.div("first", node_id="upd_10")
        target.set_value("^.fresh10")
        assert self.pointer_map["myform.fresh10"] == {id(target): target}

    def test_11_upd_value_scalar_to_bag(self) -> None:
        """value scalar → bag: la nuova discendenza viene registrata."""
        body = self.node_by_id("body")
        target = body.div("first", node_id="upd_11")
        sub = self.new_root()
        leaf = sub.div("^.fresh11")
        target.set_value(sub)
        assert self.pointer_map["myform.fresh11"] == {id(leaf): leaf}

    def test_12_upd_value_pointer_to_scalar(self) -> None:
        """value pointer → scalar: la vecchia entry di ``node`` sparisce."""
        body = self.node_by_id("body")
        target = body.div("^.fresh12", node_id="upd_12")
        assert "myform.fresh12" in self.pointer_map
        target.set_value("plain")
        assert "myform.fresh12" not in self.pointer_map

    def test_13_upd_value_pointer_to_pointer(self) -> None:
        """value pointer → pointer: la vecchia entry sparisce, la nuova si registra."""
        body = self.node_by_id("body")
        target = body.div("^.fresh13_a", node_id="upd_13")
        target.set_value("^.fresh13_b")
        assert "myform.fresh13_a" not in self.pointer_map
        assert self.pointer_map["myform.fresh13_b"] == {id(target): target}

    def test_14_upd_value_pointer_to_bag(self) -> None:
        """value pointer → bag: la vecchia entry sparisce, la nuova discendenza si registra."""
        body = self.node_by_id("body")
        target = body.div("^.fresh14_old", node_id="upd_14")
        sub = self.new_root()
        leaf = sub.div("^.fresh14_new")
        target.set_value(sub)
        assert "myform.fresh14_old" not in self.pointer_map
        assert self.pointer_map["myform.fresh14_new"] == {id(leaf): leaf}

    def test_15_upd_value_bag_to_scalar(self) -> None:
        """value bag → scalar: la vecchia discendenza viene deregistrata."""
        body = self.node_by_id("body")
        target = body.div(node_id="upd_15")
        sub = self.new_root()
        sub.div("^.fresh15")
        target.set_value(sub)
        assert "myform.fresh15" in self.pointer_map
        target.set_value("plain")
        assert "myform.fresh15" not in self.pointer_map

    def test_16_upd_value_bag_to_pointer(self) -> None:
        """value bag → pointer: la vecchia discendenza deregistrata, ``node`` si registra."""
        body = self.node_by_id("body")
        target = body.div(node_id="upd_16")
        sub = self.new_root()
        sub.div("^.fresh16_old")
        target.set_value(sub)
        target.set_value("^.fresh16_new")
        assert "myform.fresh16_old" not in self.pointer_map
        assert self.pointer_map["myform.fresh16_new"] == {id(target): target}

    def test_17_upd_value_bag_to_bag(self) -> None:
        """value bag → bag: la vecchia discendenza deregistrata, la nuova registrata."""
        body = self.node_by_id("body")
        target = body.div(node_id="upd_17")
        sub_old = self.new_root()
        sub_old.div("^.fresh17_old")
        target.set_value(sub_old)
        sub_new = self.new_root()
        new_leaf = sub_new.div("^.fresh17_new")
        target.set_value(sub_new)
        assert "myform.fresh17_old" not in self.pointer_map
        assert self.pointer_map["myform.fresh17_new"] == {id(new_leaf): new_leaf}

    def test_18_upd_attr_scalar_to_scalar(self) -> None:
        """attr scalar → scalar: ``pointer_map`` unchanged."""
        body = self.node_by_id("body")
        target = body.div(color="red", node_id="upd_18")
        before = dict(self.pointer_map)
        target.set_attr({"color": "blue"})
        assert self.pointer_map == before

    def test_19_upd_attr_scalar_to_pointer(self) -> None:
        """attr scalar → pointer: a new entry is registered for ``node``."""
        body = self.node_by_id("body")
        target = body.div(color="red", node_id="upd_19")
        target.set_attr({"color": "^.fresh19"})
        assert self.pointer_map["myform.fresh19?color"] == {id(target): target}

    def test_20_upd_attr_pointer_to_scalar(self) -> None:
        """attr pointer → scalar: la vecchia entry sparisce."""
        body = self.node_by_id("body")
        target = body.div(color="^.fresh20", node_id="upd_20")
        assert "myform.fresh20?color" in self.pointer_map
        target.set_attr({"color": "red"})
        assert "myform.fresh20?color" not in self.pointer_map

    def test_21_upd_attr_pointer_to_pointer(self) -> None:
        """attr pointer → pointer: la vecchia entry sparisce, la nuova si registra."""
        body = self.node_by_id("body")
        target = body.div(color="^.fresh21_a", node_id="upd_21")
        target.set_attr({"color": "^.fresh21_b"})
        assert "myform.fresh21_a?color" not in self.pointer_map
        assert self.pointer_map["myform.fresh21_b?color"] == {id(target): target}

    def test_22_upd_value_attr_combined(self) -> None:
        """value_attr: value e attr aggiornati insieme, entrambe le entry sistemate."""
        body = self.node_by_id("body")
        target = body.div("^.fresh22_v_old", color="^.fresh22_c_old", node_id="upd_22")
        assert "myform.fresh22_v_old" in self.pointer_map
        assert "myform.fresh22_c_old?color" in self.pointer_map
        target.set_value(
            "^.fresh22_v_new",
            _attributes={"color": "^.fresh22_c_new"},
        )
        assert "myform.fresh22_v_old" not in self.pointer_map
        assert "myform.fresh22_c_old?color" not in self.pointer_map
        assert self.pointer_map["myform.fresh22_v_new"] == {id(target): target}
        assert self.pointer_map["myform.fresh22_c_new?color"] == {id(target): target}


def test_ins_phase_2_mapkeep():
    """Drive every ``test_NN_*`` step on ``PageTester`` in alphabetical order.

    After each step, walk ``pointer_map`` and verify that every registered
    node carries a pointer (in ``value`` or in ``attr[name]`` depending on
    the key) whose absolute composition equals the path under which the
    node is filed. This is a structural coherence check on the whole map.
    """
    page = PageTester()
    page.create()
    assert page.pointer_map == {}
    for name in sorted(n for n in dir(page) if n.startswith("test_")):
        getattr(page, name)()
        for path, entry in page.pointer_map.items():
            if "?" in path:
                _, attr_name = path.rsplit("?", 1)
            else:
                attr_name = None
            for node in entry.values():
                pointer = node.attr[attr_name] if attr_name else node.value
                composed = node.abs_datapath(pointer)
                if attr_name:
                    composed = f"{composed}?{attr_name}"
                assert composed == path
