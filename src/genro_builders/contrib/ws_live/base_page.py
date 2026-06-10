# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""WsLivePage — HtmlBuilder base for the ws_live pages.

A ws_live page builds CONTENT only: the shell (resource links, the
``mainWindow`` div, the GenroClient bootstrap) is the fixed startup
page the HTTP route serves, the same for every page. The page's
``main(root)`` populates the source that the ``main`` WSX call renders
into the main div; later mutations travel as patches.
"""

from __future__ import annotations

from typing import Any

from ..html import HtmlBuilder


class _NodeAccessor:
    """Subscript access to source nodes by id: ``page.node["page"]``."""

    def __init__(self, builder: WsLivePage) -> None:
        self.builder = builder

    def __getitem__(self, node_id: str) -> Any:
        return self.builder.node_by_id(node_id)


class WsLivePage(HtmlBuilder):
    """HtmlBuilder for ws_live content. Subclass and override ``main``."""

    def set_data(self, path: str, value: Any) -> None:
        """Shortcut for ``self.data.set_item(path, value)``."""
        self.data.set_item(path, value)

    @property
    def node(self) -> _NodeAccessor:
        """Subscript accessor: ``page.node["page"]`` -> source node by id."""
        return _NodeAccessor(self)
