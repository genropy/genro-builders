# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""WsLivePage — HtmlBuilder base for the ws_live POC pages.

A ws_live page is a single HtmlBuilder. Its ``main`` calls
``self.cornice(root)`` to build the SPA shell — ``<head>`` with the CSS/JS
resource links, a right panel and the left ``<div>`` — and gets back the
left pane node, which it then populates with the page's own content.

Two sibling data branches live on the same builder: ``shell`` (the
cornice's own data — REPL/connection state) and ``left`` (the page
content's data). The shell is plain HTML composition: same dialect, so no
sub-builder, no iframe, no file. The first render is server-side; later
mutations travel over the WebSocket and re-render into the left pane.
"""

from __future__ import annotations

from typing import Any

from ..html import HtmlBuilder


class _NodeAccessor:
    """Subscript access to source nodes by id: ``page.node["ws-left"]``."""

    def __init__(self, builder: WsLivePage) -> None:
        self.builder = builder

    def __getitem__(self, node_id: str) -> Any:
        return self.builder.node_by_id(node_id)


class WsLivePage(HtmlBuilder):
    """HtmlBuilder + ws_live shell. Subclass and override ``main``."""

    def cornice(self, root: Any) -> Any:
        """Build the SPA shell into ``root``; return the left pane node.

        Lays out ``<html><head>`` (title + CSS/JS resource links) and a
        ``<body>`` split into a left pane (``datapath="left"`` — the live
        document) and a right panel (``datapath="shell"`` — placeholder for
        the REPL/trees). The two datapaths are siblings, not nested. The
        caller populates the returned left pane with the page content.
        """
        html = root.html()
        head = html.head()
        head.meta(charset="UTF-8")
        head.title("Genro Builders — ws_live")
        head.link(rel="stylesheet", href="../static?file=ws_live.css")
        head.script(src="../static?file=ws_live.js")
        body = html.body()
        left = body.div(class_="ws-left", node_id="ws-left", datapath="left")
        body.div("REPL panel", class_="ws-right", datapath="shell")
        return left

    def set_data(self, path: str, value: Any) -> None:
        """Shortcut for ``self.data.set_item(path, value)``."""
        self.data.set_item(path, value)

    @property
    def node(self) -> _NodeAccessor:
        """Subscript accessor: ``page.node["ws-left"]`` -> source node by id."""
        return _NodeAccessor(self)
