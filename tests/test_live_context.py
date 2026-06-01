# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for the RX livello 0 reactive context manager ``handler.live()``.

Validates the test contract of ``roadmap/reactivity/contract.md``:

    1. ``live()`` before ``create()`` -> RuntimeError (DR5).
    2. ``live()`` with no explicit target uses the handler's default
       target registered via ``set_render_target(..., default=True)`` (DR2).
    3. Without ``with``: a ``data.set_item`` does NOT write the target (DR6).
    4. Inside ``with live(out)``: ``data.set_item`` re-renders to the file (DR3).
    5. Inside ``with live(out)``: ``node.set_attr`` re-renders to the file (DR3).
    6. Re-entry: nested ``live`` switches the active target and restores the
       outer one on exit, no deadlock (DR4).

All mutations go through the canonical API (``data.set_item``,
``node.set_attr``), never via direct attribute assignment.
"""
from __future__ import annotations

import pytest

from genro_builders.contrib.html import HtmlBuilderHandler


class Page(HtmlBuilderHandler):
    def main(self, root) -> None:
        body = root.body(datapath="page", node_id="body")
        body.h1("^.title", node_id="h1")


def test_live_before_create_raises() -> None:
    page = Page()
    with pytest.raises(RuntimeError), page.live():
        pass


def test_live_uses_default_target(tmp_path) -> None:
    page = Page()
    page.create()
    out = tmp_path / "out.html"
    page.set_render_target("html", str(out), default=True)
    with page.live():
        page.data.set_item("page.title", "Default")
    assert out.exists()
    assert "Default" in out.read_text()


def test_no_render_without_with(tmp_path) -> None:
    page = Page()
    page.create()
    out = tmp_path / "out.html"
    page.data.set_item("page.title", "Hello")
    assert not out.exists()


def test_data_mutation_renders_to_file(tmp_path) -> None:
    page = Page()
    page.create()
    out = tmp_path / "out.html"
    with page.live(str(out)):
        page.data.set_item("page.title", "Hello")
        assert out.exists()
        assert "Hello" in out.read_text()
        page.data.set_item("page.title", "World")
    html = out.read_text()
    assert "World" in html
    assert "Hello" not in html


def test_source_attr_mutation_renders_to_file(tmp_path) -> None:
    page = Page()
    page.create()
    out = tmp_path / "out.html"
    with page.live(str(out)):
        page.data.set_item("page.title", "Hello")
        body = page.node_by_id("body")
        body.set_attr({"style": "color:red"})
    html = out.read_text()
    assert "color: red" in html


def test_reentry_restores_outer_target(tmp_path) -> None:
    page = Page()
    page.create()
    t1 = str(tmp_path / "t1.html")
    t2 = str(tmp_path / "t2.html")
    with page.live(t1):
        assert page._live_target == t1
        with page.live(t2):
            assert page._live_target == t2
            page.data.set_item("page.title", "Inner")
        assert page._live_target == t1
        assert page._live_active is True
    assert page._live_active is False


def test_setup_runs_before_main() -> None:
    """create() calls setup() before main(); main can read the seeded data."""
    class SeededPage(HtmlBuilderHandler):
        def setup(self) -> None:
            self.data.set_item("rows.a.name", "Alpha")
            self.data.set_item("rows.b.name", "Beta")

        def main(self, root) -> None:
            body = root.body(datapath="rows", node_id="body")
            codes = list(self.data["rows"].keys())
            for code in codes:
                body.div(f"^.{code}.name", node_id=f"row_{code}")

    page = SeededPage()
    page.create()
    html = page.render(target=False)
    assert "Alpha" in html
    assert "Beta" in html


def test_live_enter_exit_hooks_fire_once_per_section() -> None:
    """on_live_enter/on_live_exit fire once per section, exit even on error."""
    events: list[str] = []

    class HookedPage(HtmlBuilderHandler):
        def main(self, root) -> None:
            root.body(datapath="page", node_id="body").h1("^.t", node_id="h1")

        def on_live_enter(self) -> None:
            events.append("enter")

        def on_live_exit(self) -> None:
            events.append("exit")

    page = HookedPage()
    page.create()
    with page.live():
        page.data.set_item("page.t", "A")
        page.data.set_item("page.t", "B")
    assert events == ["enter", "exit"]

    events.clear()
    with pytest.raises(ValueError), page.live():
        raise ValueError("boom")
    assert events == ["enter", "exit"]
