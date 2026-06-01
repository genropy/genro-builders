# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Unit tests for ``LiveDemoApp`` route handlers.

Route methods are plain sync methods of ``LiveDemoApp`` — they can be
called directly in tests with no asyncio, no fake transport, no server
on a real socket. We invoke ``repl(...)`` / ``out()`` / the tree routes
on a fresh app instance and check the observable result: the rendered
``out.html`` and the tree snapshots.

The REPL namespace exposes a single name, ``page``; snippets mutate the
document through the canonical builder API.

End-to-end routing (the ``@route()`` decorator + ``WsxHandler``
dispatch) is covered in ``test_live_demo_e2e.py``.
"""
from __future__ import annotations

import pytest

pytest.importorskip("genro_asgi")
pytest.importorskip("genro_routes")

from genro_builders.contrib.live import LiveDemoApp


@pytest.fixture
def app() -> LiveDemoApp:
    """Fresh app, current demo set to ``basic`` (seeded ``Hello``/``Scrivi…``).

    Selected explicitly so these tests do not depend on which demo happens
    to sort first among the auto-discovered pages.
    """
    instance = LiveDemoApp()
    instance.select("basic")
    return instance


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------


def test_out_contains_seed_data(app: LiveDemoApp) -> None:
    """``on_init`` renders the seeded title and message to out.html."""
    html = app.out()
    assert "Hello" in html
    assert "Scrivi codice Python nella REPL." in html


def test_initial_data_tree_keys(app: LiveDemoApp) -> None:
    """``page.data`` exposes the two seeded keys under ``page``."""
    page_entry = app.tree_data()["data"]["children"][0]
    keys = {child["key"] for child in page_entry["children"]}
    assert {"title", "message"} <= keys


# ---------------------------------------------------------------------------
# REPL — data mutations
# ---------------------------------------------------------------------------


def test_repl_set_data_updates_out(app: LiveDemoApp) -> None:
    """A snippet writing into page.data re-renders out.html."""
    result = app.repl('page.data.set_item("page.title", "Live!")')
    assert result["ok"] is True
    html = app.out()
    assert "Live!" in html
    assert "Hello" not in html


def test_repl_namespace_persists_across_runs(app: LiveDemoApp) -> None:
    """Variables defined in one snippet survive into the next (real REPL)."""
    app.repl("x = 7")
    result = app.repl('page.data.set_item("page.title", str(x * 6))')
    assert result["ok"] is True
    assert "42" in app.out()


def test_repl_error_is_returned_not_raised(app: LiveDemoApp) -> None:
    """A failing snippet returns ``ok=False`` + error text, does not raise."""
    result = app.repl("1 / 0")
    assert result["ok"] is False
    assert "ZeroDivisionError" in result["error"]


# ---------------------------------------------------------------------------
# REPL — attribute and structure mutations
# ---------------------------------------------------------------------------


def test_repl_set_attr_applies_to_out(app: LiveDemoApp) -> None:
    """A snippet setting an attribute ends up in the rendered tag.

    The renderer normalises CSS (``color:red`` → ``color: red``).
    """
    result = app.repl(
        'page.node_by_id("h1").set_attr({"style": "color:red"})',
    )
    assert result["ok"] is True
    assert "color: red" in app.out()


def test_repl_add_child_appends_tag(app: LiveDemoApp) -> None:
    """A snippet appending a child re-renders out.html with the new node."""
    result = app.repl('page.node_by_id("body").p("aggiunto", _class="note")')
    assert result["ok"] is True
    html = app.out()
    assert "aggiunto" in html
    assert 'class="note"' in html


# ---------------------------------------------------------------------------
# Multi-demo: menu, select, per-demo namespace
# ---------------------------------------------------------------------------


def test_menu_lists_discovered_demos(app: LiveDemoApp) -> None:
    """``menu`` lists every auto-discovered demo plus the current key."""
    m = app.menu()
    keys = {d["key"] for d in m["demos"]}
    assert {"basic", "dashboard", "signup"} <= keys
    assert m["current"] in keys


def test_select_switches_current_demo(app: LiveDemoApp) -> None:
    """``select`` switches the current demo and re-renders it to out.html."""
    result = app.select("dashboard")
    assert result["ok"] is True
    assert result["current"] == "dashboard"
    assert "Dashboard" in app.out()


def test_select_unknown_demo_returns_error(app: LiveDemoApp) -> None:
    """Selecting an unknown demo returns ``ok=False`` (does not raise)."""
    result = app.select("nope")
    assert result["ok"] is False
    assert "nope" in result["error"]


def test_out_xml_is_raw_source_view(app: LiveDemoApp) -> None:
    """``out_xml`` returns the document as raw XML: indented, pointers
    unresolved (the structural view, distinct from the rendered HTML)."""
    xml = app.out_xml()
    assert "^.title" in xml          # pointer shown raw, not resolved
    assert "Hello" not in xml         # the resolved value lives in HTML, not here


def test_repl_source_mutation_updates_out_xml(app: LiveDemoApp) -> None:
    """A snippet that mutates the source updates out_xml (via on_live_exit)."""
    app.repl('page.node["body"].p("added", node_id="extra")')
    assert "extra" in app.out_xml()


def test_source_code_returns_current_demo_module(app: LiveDemoApp) -> None:
    """``source_code`` returns the Python source of the current demo."""
    code = app.source_code()["source_code"]
    assert "class Demo" in code
    app.select("dashboard")
    assert "Dashboard demo" in app.source_code()["source_code"]


def test_repl_namespace_is_per_demo(app: LiveDemoApp) -> None:
    """Variables defined under one demo do not leak into another."""
    app.select("dashboard")
    app.repl("marker = 123")
    app.select("basic")
    result = app.repl('page.set_data("page.title", str(marker))')
    assert result["ok"] is False
    assert "NameError" in result["error"]


# ---------------------------------------------------------------------------
# Tree snapshots
# ---------------------------------------------------------------------------


def test_repl_response_includes_trees(app: LiveDemoApp) -> None:
    """``repl`` returns source + data tree snapshots (no html field)."""
    result = app.repl('page.data.set_item("page.title", "X")')
    assert "source" in result
    assert "data" in result
    assert "html" not in result


def test_source_tree_walks_the_document(app: LiveDemoApp) -> None:
    """The source tree exposes body → link, h1, p with the right shape.

    The leading ``link`` is the shared-stylesheet link added by
    ``link_stylesheet`` at the top of every demo's ``main()``.
    """
    src = app.tree_source()["source"]
    assert src["kind"] == "root"
    body = src["children"][0]
    assert body["tag"] == "body"
    assert body["value"]["kind"] == "bag"
    tags = [child["tag"] for child in body["children"]]
    assert tags == ["link", "h1", "p"]
    h1 = next(c for c in body["children"] if c["tag"] == "h1")
    assert h1["value"]["kind"] == "pointer"
    assert h1["value"]["raw"] == "^.title"
    assert h1["value"]["pointer_kind"] == "caret"


def test_data_tree_walks_the_bag(app: LiveDemoApp) -> None:
    """The data tree exposes page → {title, message} as scalars."""
    data = app.tree_data()["data"]
    assert data["kind"] == "root"
    page_entry = data["children"][0]
    assert page_entry["key"] == "page"
    assert page_entry["kind"] == "bag"
    keys = {child["key"]: child for child in page_entry["children"]}
    assert keys["title"]["kind"] == "scalar"
    assert keys["title"]["value"] == "Hello"
    assert keys["message"]["value"] == "Scrivi codice Python nella REPL."


def test_repl_refreshes_data_tree(app: LiveDemoApp) -> None:
    """After a snippet the returned data tree carries the new value."""
    result = app.repl('page.data.set_item("page.title", "Tree!")')
    page_entry = result["data"]["children"][0]
    title = next(c for c in page_entry["children"] if c["key"] == "title")
    assert title["value"] == "Tree!"


def test_repl_add_child_updates_source_tree(app: LiveDemoApp) -> None:
    """A snippet adding a node makes it visible in the returned source tree."""
    result = app.repl('page.node_by_id("body").span("extra")')
    body = result["source"]["children"][0]
    child_tags = [c["tag"] for c in body["children"]]
    assert "span" in child_tags
