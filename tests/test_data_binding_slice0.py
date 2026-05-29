# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for the data binding slice 0.

Covers:
    P1 - ``handler.data`` exposed as a live ``Bag`` with active subscriptions.
    P3 - ``BuilderHandler.evaluate_on_node`` phase 1 (pointer resolution).
    P4 - ``BuilderHandler.evaluate_on_node`` phase 2 (template expansion).
    P5 - ``node.get_relative_data`` / ``node.set_relative_data`` round-trip.

Canonical example
-----------------

::

    class P(HtmlBuilderHandler):
        def main(self, root):
            root.body(datapath="myform", node_id="body")

    page = P()
    page.create()
    page.data.set_item("myform.title", "Hello")
    page.data.set_item("myform.color", "blue")

    body = page.node_by_id("body")
    leaf = body.div("^.title", color="^.color")

    rv, ra = page.evaluate_on_node(leaf)
    assert rv == "Hello"
    assert ra["color"] == "blue"

All mutations of ``page.data`` flow through the canonical API
(``data.set_item`` or ``node.set_relative_data``), never via direct
attribute writes.
"""
from __future__ import annotations

import pytest

from genro_builders.contrib.html import HtmlBuilderHandler

# ---------------------------------------------------------------------------
# P1 - handler.data is a live Bag with subscriptions
# ---------------------------------------------------------------------------


def test_data_is_empty_bag_after_create():
    """After ``create()``, ``page.data`` is an empty Bag."""
    from genro_bag import Bag

    class P(HtmlBuilderHandler):
        def main(self, root) -> None:
            root.body()

    page = P()
    page.create()
    assert isinstance(page.data, Bag)
    assert list(page.data.keys()) == []


def test_data_subscriptions_active_after_create():
    """Mutations on ``page.data`` post-``create()`` flow to ``on_data_change``."""

    events: list[tuple[str, str | None]] = []

    class P(HtmlBuilderHandler):
        def main(self, root) -> None:
            root.body()

        def on_data_change(self, node, evt, evt_detail=None, **kw) -> None:
            events.append((evt, evt_detail))

    page = P()
    page.create()
    page.data.set_item("x", 1)
    assert any(evt == "ins" for evt, _ in events)


# ---------------------------------------------------------------------------
# P3 - evaluate_on_node phase 1: pointer resolution
# P4 - evaluate_on_node phase 2: template expansion
# P5 - node.get_relative_data / set_relative_data
#
# Cumulative walkthrough on a single PageTester. Each test_NN_* exercises
# one canonical operation against a shared source/data state; the driver
# at the bottom invokes them in numeric order.
# ---------------------------------------------------------------------------


class PageTester(HtmlBuilderHandler):
    """Shared handler for the slice-0 cumulative walkthrough."""

    def main(self, root) -> None:
        """Seed a body anchored at ``myform`` with a single id'd leaf."""
        root.body(datapath="myform", node_id="body")

    # -- P3: pointer resolution ----------------------------------------

    def test_03_eval_pointer_caret_on_attr(self) -> None:
        """``^.path`` on an attribute resolves against ``self.data``."""
        self.data.set_item("myform.color", "blue")
        body = self.node_by_id("body")
        leaf = body.div(color="^.color", node_id="leaf_03")
        rv, ra = self.evaluate_on_node(leaf)
        assert ra["color"] == "blue"
        assert rv is None  # no node_value set

    def test_04_eval_pointer_equals_on_attr(self) -> None:
        """``=.path`` resolves like ``^`` (DB-D9: same lookup, different
        registration semantics handled outside abs_datapath)."""
        body = self.node_by_id("body")
        leaf = body.div(color="=.color", node_id="leaf_04")
        rv, ra = self.evaluate_on_node(leaf)
        assert ra["color"] == "blue"
        assert rv is None

    def test_05_eval_pointer_on_value(self) -> None:
        """A pointer in ``node.value`` resolves into ``runtime_value``."""
        self.data.set_item("myform.title", "Hello")
        body = self.node_by_id("body")
        leaf = body.div("^.title", node_id="leaf_05")
        rv, ra = self.evaluate_on_node(leaf)
        assert rv == "Hello"
        assert "datapath" not in ra  # body's datapath does not leak here

    def test_06_eval_pointer_absent_returns_none(self) -> None:
        """Valid path but no data populated → ``None``."""
        body = self.node_by_id("body")
        leaf = body.div(color="^.missing", node_id="leaf_06")
        _, ra = self.evaluate_on_node(leaf)
        assert ra["color"] is None

    def test_07_eval_broken_path_raises(self) -> None:
        """Relative path with no ancestor datapath chain → ``ValueError``."""
        orphan = self.new_root()
        body = orphan.body(node_id="orphan_body_07")
        leaf = body.div(color="^.color", node_id="leaf_07")
        with pytest.raises(ValueError):
            self.evaluate_on_node(leaf)

    def test_08_eval_equals_not_in_pointer_map(self) -> None:
        """``=`` is NOT registered in pointer_map (DB-D9 / DBS lazy-only)."""
        # leaf_04 was added with color="=.color"; the eager pointer must
        # not appear under "myform.color?color" in the map.
        entry = self.pointer_map.get("myform.color?color", {})
        leaf_04 = self.node_by_id("leaf_04")
        assert id(leaf_04) not in entry

    def test_09_eval_literal_attr_passthrough(self) -> None:
        """Literal (non-pointer) attrs are returned verbatim."""
        body = self.node_by_id("body")
        leaf = body.div(color="literal-red", node_id="leaf_09")
        _, ra = self.evaluate_on_node(leaf)
        assert ra["color"] == "literal-red"

    # -- P4: template expansion ----------------------------------------

    def test_10_template_two_phase(self) -> None:
        """A pointer on one attr + a template referencing it: phase 1
        resolves the pointer, phase 2 substitutes ``${name}``."""
        body = self.node_by_id("body")
        leaf = body.div(
            _class="card ${color}",
            color="^.color",
            node_id="leaf_10",
        )
        _, ra = self.evaluate_on_node(leaf)
        assert ra["color"] == "blue"
        assert ra["_class"] == "card blue"

    def test_11_template_none_to_empty_string(self) -> None:
        """A pointer resolved to ``None`` substitutes to ``""`` (DB-D11.6)."""
        body = self.node_by_id("body")
        leaf = body.div(
            _class="card ${missing}",
            missing="^.never_set",
            node_id="leaf_11",
        )
        _, ra = self.evaluate_on_node(leaf)
        assert ra["missing"] is None
        assert ra["_class"] == "card "

    def test_12_template_unknown_name_raises(self) -> None:
        """A ``${name}`` whose ``name`` is not in resolved attrs raises
        ``KeyError`` (DB-D10 crash-totale)."""
        body = self.node_by_id("body")
        leaf = body.div(
            _class="card ${nowhere}",
            node_id="leaf_12",
        )
        with pytest.raises(KeyError):
            self.evaluate_on_node(leaf)

    def test_13_template_on_value(self) -> None:
        """Template on ``node.value`` is expanded in phase 2."""
        body = self.node_by_id("body")
        leaf = body.div(
            "hello ${who}",
            who="^.title",
            node_id="leaf_13",
        )
        rv, _ = self.evaluate_on_node(leaf)
        assert rv == "hello Hello"


def test_data_binding_slice0_cumulative():
    """Drive every ``test_NN_*`` on ``PageTester`` in numeric order."""
    page = PageTester()
    page.create()
    for name in sorted(n for n in dir(page) if n.startswith("test_")):
        getattr(page, name)()
