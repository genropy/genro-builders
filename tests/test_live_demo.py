# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Unit tests for ``LiveDemoApp`` route handlers.

Route methods are plain sync methods of ``LiveDemoApp`` — they can be
called directly in tests with no asyncio, no fake transport, no server
on a real socket. We invoke each one on a fresh app instance and check
that the returned ``html`` reflects the requested mutation.

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
    """Fresh app with the default DemoPage seeded with ``Hello``/``Modifica…``."""
    return LiveDemoApp()


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------


def test_initial_render_contains_seed_data(app: LiveDemoApp) -> None:
    """The factory page renders the seeded title and message."""
    html = app.render()["html"]
    assert "Hello" in html
    assert "Modifica i dati dalla REPL." in html


def test_initial_data_keys(app: LiveDemoApp) -> None:
    """``page.data`` exposes the two seeded keys under ``page``."""
    keys = app.keys(path="page")["keys"]
    assert "title" in keys
    assert "message" in keys


# ---------------------------------------------------------------------------
# Data mutations
# ---------------------------------------------------------------------------


def test_set_data_updates_render(app: LiveDemoApp) -> None:
    """``set_data`` writes through and the new value shows up in HTML."""
    result = app.set_data(path="page.title", value="Live!")
    assert result["ok"] is True
    assert "Live!" in result["html"]
    assert "Hello" not in result["html"]


def test_get_data_round_trip(app: LiveDemoApp) -> None:
    """``set_data`` then ``get_data`` returns the value written."""
    app.set_data(path="page.title", value="Round")
    assert app.get_data(path="page.title")["value"] == "Round"


def test_set_data_into_fresh_path(app: LiveDemoApp) -> None:
    """A new path under ``page.data`` becomes addressable."""
    app.set_data(path="page.custom", value=42)
    assert app.get_data(path="page.custom")["value"] == 42
    assert "custom" in app.keys(path="page")["keys"]


# ---------------------------------------------------------------------------
# Attribute mutations
# ---------------------------------------------------------------------------


def test_set_attr_applies_to_html(app: LiveDemoApp) -> None:
    """``set_attr`` on a node id ends up in the rendered tag.

    The renderer normalises CSS declarations (``color:red`` →
    ``color: red``) when emitting the ``style`` attribute.
    """
    result = app.set_attr(node_id="h1", attr="style", value="color:red")
    assert result["ok"] is True
    assert "color: red" in result["html"]


def test_set_value_replaces_node_value(app: LiveDemoApp) -> None:
    """``set_value`` replaces ``node.value`` (overriding the pointer)."""
    result = app.set_value(node_id="msg", value="Sostituito")
    assert "Sostituito" in result["html"]


# ---------------------------------------------------------------------------
# Structure mutations
# ---------------------------------------------------------------------------


def test_add_child_appends_tag(app: LiveDemoApp) -> None:
    """``add_child`` appends a new node under the parent and re-renders."""
    result = app.add_child(parent_id="body", tag="p", text="aggiunto")
    assert result["ok"] is True
    assert "<p" in result["html"]
    assert "aggiunto" in result["html"]


def test_add_child_with_attrs(app: LiveDemoApp) -> None:
    """Extra kwargs are forwarded to the grammar element as attributes."""
    result = app.add_child(
        parent_id="body", tag="span", text="hi", _class="badge",
    )
    assert "<span" in result["html"]
    assert 'class="badge"' in result["html"]


def test_remove_child_drops_it_from_html(app: LiveDemoApp) -> None:
    """``remove_child`` removes the node by its bag label."""
    # The seeded body has h1_0 and p_0 as nested children (labels follow
    # the BagBuilder convention <tag>_<index>).
    before = app.render()["html"]
    assert "Modifica i dati dalla REPL." in before
    result = app.remove_child(parent_id="body", label="p_0")
    assert "Modifica i dati dalla REPL." not in result["html"]


# ---------------------------------------------------------------------------
# Tree snapshots
# ---------------------------------------------------------------------------


def test_render_response_includes_trees(app: LiveDemoApp) -> None:
    """``render`` returns html + source tree + data tree in one payload."""
    result = app.render()
    assert "html" in result
    assert "source" in result
    assert "data" in result


def test_source_tree_walks_the_document(app: LiveDemoApp) -> None:
    """The source tree exposes body → h1, msg with the right shape."""
    src = app.tree_source()["source"]
    assert src["kind"] == "root"
    body = src["children"][0]
    assert body["tag"] == "body"
    assert body["value"]["kind"] == "bag"
    tags = [child["tag"] for child in body["children"]]
    assert tags == ["h1", "p"]
    # The h1 carries a pointer in its value.
    h1 = body["children"][0]
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
    assert keys["message"]["value"] == "Modifica i dati dalla REPL."


def test_mutator_response_refreshes_trees(app: LiveDemoApp) -> None:
    """After ``set_data`` the data tree carries the new value."""
    result = app.set_data(path="page.title", value="Tree!")
    page_entry = result["data"]["children"][0]
    title = next(c for c in page_entry["children"] if c["key"] == "title")
    assert title["value"] == "Tree!"


def test_add_child_updates_source_tree(app: LiveDemoApp) -> None:
    """``add_child`` makes the new node visible in the next source tree."""
    result = app.add_child(parent_id="body", tag="span", text="extra")
    body = result["source"]["children"][0]
    child_tags = [c["tag"] for c in body["children"]]
    assert "span" in child_tags
