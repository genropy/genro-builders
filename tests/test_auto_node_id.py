# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for the automatic HTML ``id`` on pointer-bound nodes.

Under ``include_datapath`` (the reactive render mode), any node that
carries at least one pointer (value or attribute) gets an HTML ``id``
equal to its structural path relative to the source root
(``Bag.relative_path``) — UNLESS the author already specified an ``id``,
in which case the author's wins.

This id is the stable per-node DOM identity the (future) WebSocket patch
channel will target: "node <id> changed value". A node with no pointer is
static and gets no auto-id. Without ``include_datapath`` no auto-id is
emitted (static renders stay clean).
"""
from __future__ import annotations

from genro_builders.contrib.html import HtmlBuilderHandler


def _render(handler_cls, **opts):
    page = handler_cls()
    page.create()
    return page, page.render(**opts)


def test_auto_id_on_pointer_node_with_datapath():
    """A node with a pointer gets id=relative_path under include_datapath."""

    class P(HtmlBuilderHandler):
        def main(self, root) -> None:
            body = root.body(datapath="tri")
            body.data_setter(".area", 30)
            body.div("^.area")

    _page, html = _render(P, include_datapath=True)
    # the div has a pointer -> auto id = its path relative to source root
    assert 'id="body_0.div_0"' in html


def test_no_auto_id_without_datapath():
    """Static render (no include_datapath) emits no auto id."""

    class P(HtmlBuilderHandler):
        def main(self, root) -> None:
            body = root.body(datapath="tri")
            body.data_setter(".area", 30)
            body.div("^.area")

    _page, html = _render(P)
    assert "id=" not in html


def test_no_auto_id_on_static_node():
    """A node without pointers gets no auto id, even under include_datapath."""

    class P(HtmlBuilderHandler):
        def main(self, root) -> None:
            body = root.body()
            body.div("plain text")

    _page, html = _render(P, include_datapath=True)
    assert "id=" not in html


def test_author_id_wins():
    """An explicit author id is preserved (auto id does not override)."""

    class P(HtmlBuilderHandler):
        def main(self, root) -> None:
            body = root.body(datapath="tri")
            body.data_setter(".area", 30)
            body.div("^.area", id="myArea")

    _page, html = _render(P, include_datapath=True)
    assert 'id="myArea"' in html
    assert 'id="body_0.div_0"' not in html


def test_auto_id_on_attribute_pointer():
    """A node whose pointer is on an attribute (not value) also gets an id."""

    class P(HtmlBuilderHandler):
        def main(self, root) -> None:
            body = root.body(datapath="tri")
            body.data_setter(".color", "red")
            body.div("text", style="^.color")

    _page, html = _render(P, include_datapath=True)
    assert 'id="body_0.div_0"' in html
