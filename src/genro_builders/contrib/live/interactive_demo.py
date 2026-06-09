# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""InteractiveDemo — HtmlBuilder with REPL conveniences.

Base class for the live demo pages. Subclasses define ``main()`` only;
this class adds the handful of shortcuts the browser REPL exposes on the
``page`` object, so snippets stay short:

    page.set_data("page.title", "Ciao")   # -> data.set_item(...)
    page.node["h1"].set_attr({...})        # -> node_by_id("h1")

These conveniences live in the demo, NOT in the core ``HtmlBuilder``
(the core API stays minimal). Add new demo pages by subclassing this and
implementing ``main()``; they are auto-discovered by ``pages``.

A demo page is a builder mounted on the app's single ``BuilderHandler``;
the live section and the raw-xml view are driven by the app, not here.
"""

from __future__ import annotations

from typing import Any

from ..html import HtmlBuilder


class _NodeAccessor:
    """Subscript access to source nodes by id: ``page.node["h1"]``."""

    def __init__(self, builder: InteractiveDemo) -> None:
        self.builder = builder

    def __getitem__(self, node_id: str) -> Any:
        return self.builder.node_by_id(node_id)


class InteractiveDemo(HtmlBuilder):
    """HtmlBuilder + REPL shortcuts. Subclass and override ``main``.

    The HTML view is rendered with the datapath hooks on
    (``include_datapath``) so the browser can write user input back to the
    matching data path; the raw ``xml`` view (structural source) is left to
    the app.
    """

    def set_data(self, path: str, value: Any) -> None:
        """Shortcut for ``self.data.set_item(path, value)``."""
        self.data.set_item(path, value)

    def render(self, mode=None, target=None, **opts):
        """Render with datapath hooks turned on for the HTML view.

        The demo's HTML carries ``data-<name>-pointer`` attributes so the
        browser can write user input back to the matching data path. The
        raw ``xml`` view is left untouched (it shows the structural source,
        pointers unresolved).
        """
        effective_mode = mode or self._default_render_mode
        if effective_mode == "html":
            opts.setdefault("include_datapath", True)
        return super().render(mode=mode, target=target, **opts)

    @property
    def node(self) -> _NodeAccessor:
        """Subscript accessor: ``page.node["body"]`` -> source node by id."""
        return _NodeAccessor(self)
