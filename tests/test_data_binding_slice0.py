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
