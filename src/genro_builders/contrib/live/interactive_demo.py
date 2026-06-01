# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""InteractiveDemo — HtmlBuilderHandler with REPL conveniences.

Base class for the live demo pages. Subclasses define ``main()`` only;
this class adds the handful of shortcuts the browser REPL exposes on the
``page`` object, so snippets stay short:

    page.set_data("page.title", "Ciao")   # -> data.set_item(...)
    page.node["h1"].set_attr({...})        # -> node_by_id("h1")

These conveniences live in the demo, NOT in the core ``HtmlBuilderHandler``
(the core API stays minimal). Add new demo pages by subclassing this and
implementing ``main()``; they are auto-discovered by ``pages``.
"""

from __future__ import annotations

from typing import Any

from ..html import HtmlBuilderHandler


class _NodeAccessor:
    """Subscript access to source nodes by id: ``page.node["h1"]``."""

    def __init__(self, handler: InteractiveDemo) -> None:
        self.handler = handler

    def __getitem__(self, node_id: str) -> Any:
        return self.handler.node_by_id(node_id)


class InteractiveDemo(HtmlBuilderHandler):
    """HtmlBuilderHandler + REPL shortcuts. Subclass and override ``main``."""

    def seed(self) -> None:
        """Seed initial data. Override to populate ``self.data`` after
        ``create()``. Default is a no-op (the page starts with empty data).
        """

    def set_data(self, path: str, value: Any) -> None:
        """Shortcut for ``self.data.set_item(path, value)``."""
        self.data.set_item(path, value)

    @property
    def node(self) -> _NodeAccessor:
        """Subscript accessor: ``page.node["body"]`` -> source node by id."""
        return _NodeAccessor(self)
