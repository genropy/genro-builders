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
    """HtmlBuilderHandler + REPL shortcuts. Subclass and override ``main``.

    Beyond the shortcuts, this overrides :meth:`on_live_exit` to emit a
    second, raw rendering of the document (mode ``xml``, pretty) at the end
    of every live section — a structural view that shows the source markup
    (pointers unresolved, indented), next to the resolved HTML. The app
    registers the ``xml`` render target; if none is registered the render
    is a harmless no-op (returns a string, writes nowhere).
    """

    def set_data(self, path: str, value: Any) -> None:
        """Shortcut for ``self.data.set_item(path, value)``."""
        self.data.set_item(path, value)

    @property
    def node(self) -> _NodeAccessor:
        """Subscript accessor: ``page.node["body"]`` -> source node by id."""
        return _NodeAccessor(self)

    def on_live_exit(self) -> None:
        """Emit the raw (xml, pretty) rendering at the end of a live section.

        Uses the ``xml`` render target registered by the app. The HTML is
        already kept current by the per-mutation render (DR3); this adds the
        structural raw view once per section (DR9).
        """
        self.render(mode="xml", pretty=True)
