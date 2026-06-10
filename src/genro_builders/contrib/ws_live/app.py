# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""WsLiveApp — POC: server-side SPA, no out.html file, no iframe.

A page is a single HtmlBuilder (a WsLivePage): its ``main`` builds the SPA
shell via ``self.cornice(root)`` and populates the left pane. The first
render is server-side, returned by the ``page`` HTTP route as a full HTML
string (first paint). Later mutations travel over the WebSocket: the
``mutate`` WSX route applies the change inside ``handler.live()`` and
returns the re-rendered HTML, which the JS client injects into the left
pane. No file is written, no iframe is used.

HTTP and WebSocket are distinct connections. The GET render is one-shot
(paint then discard); the WS keeps its own per-connection page instances in
``ws.state`` (lazy-prepared on the first mutation that names a page).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from genro_asgi import AsgiApplication
from genro_asgi.request import get_current_request
from genro_routes import route

from genro_builders.builder import BuilderHandler

from . import pages

_PACKAGE_DIR = Path(__file__).parent


class WsLiveApp(AsgiApplication):
    """Server-side reactive SPA over WSX, one HtmlBuilder per page."""

    def __init__(self, **kwargs: Any) -> None:
        """Wire ``base_dir`` to the package directory by default."""
        kwargs.setdefault("base_dir", _PACKAGE_DIR)
        super().__init__(**kwargs)

    def on_init(self, **kwargs: Any) -> None:
        """Discover the pages once: ``{key: (title, PageClass)}``."""
        self.pages = pages.discover()

    def _prepare(self, key: str) -> Any:
        """Instantiate and mount the page ``key`` on its own handler.

        Returns the created builder. Each page is a single builder mounted
        on its own ``BuilderHandler`` (this app is the application, so the
        handler is reactive). ``add_builder`` runs ``create`` (setup + main
        + first calculation); ``activate`` renders once and arms the data
        subscribe (only this one builder, so it renders only this page).
        """
        title, page_class = self.pages[key]
        builder = page_class()
        handler = BuilderHandler(application=self)
        handler.add_builder(builder)
        handler.activate()
        return builder

    # ------------------------------------------------------------------
    # HTTP — serve the page shell (first paint, server-side render)
    # ------------------------------------------------------------------

    @route(meta_mime_type="text/html")
    def page(self, *args: str) -> str:
        """Render a page to HTML (cornice + content). ``/<app>/page/<key>``.

        The page key is the first path segment after ``page`` (defaults to
        the first discovered page). The builder is one-shot: it paints the
        first view; the live instance is (re)prepared on the WS side.
        """
        key = args[0] if args else next(iter(self.pages))
        builder = self._prepare(key)
        html = builder.render(target=False, include_datapath=True)
        return "<!DOCTYPE html>\n" + html

    @route()
    def static(self, file: str = "") -> Path:
        """Serve a static resource (JS, CSS) from ``resources/``.

        Returns a ``Path``; ``set_result`` detects the mime type from the
        suffix. Raises on missing file or empty parameter.
        """
        if not file:
            raise ValueError("file parameter required")
        resource_path = _PACKAGE_DIR / "resources" / file
        if not resource_path.is_file():
            raise FileNotFoundError(f"resource not found: {file}")
        return resource_path

    # ------------------------------------------------------------------
    # WSX — mutate the live page (per-connection, lazy-prepared)
    # ------------------------------------------------------------------

    @route()
    def mutate(self, page: str = "", path: str = "", value: Any = None) -> dict[str, Any]:
        """Apply a data mutation to the live page and return the patches.

        The live page instances live per-connection in ``ws.state.pages``,
        keyed by page key; the first mutation naming a page prepares it.
        The write runs inside ``handler.live()`` so the readers are queued;
        the patches (one ``{id, html}`` per re-rendered node) are collected
        inside the section — under the handler lock — so a concurrent mutate
        cannot mix its own touched nodes into this one's queue. The JS client
        swaps each node by id, leaving the focused input untouched.
        """
        request = get_current_request()
        ws = request.websocket
        if "pages" not in ws.state:
            ws.state.pages = {}
        registry = ws.state.pages
        builder = registry.get(page)
        if builder is None:
            builder = self._prepare(page)
            registry[page] = builder
        handler = builder.handler
        with handler.live():
            handler.data.set_item(path, value)
            patches = self._render_patches(builder, handler)
        return {"ok": True, "patches": patches}

    def _render_patches(self, builder: Any, handler: Any) -> list[dict[str, str]]:
        """Render only the queued nodes into ``[{id, html}, ...]``.

        Partial render (granularity "node"): for each path in the live
        render queue, resolve the source node and render just that node;
        the ``id`` is the builder-relative path, matching the ``id``
        emitted in the DOM by ``include_datapath``.
        """
        renderer = type(builder).renderer_html.__get__(builder, type(builder))
        patches: list[dict[str, str]] = []
        for paths in handler._nodes_to_render.values():
            for full in paths:
                rel = full.split(".", 1)[1] if "." in full else full
                node = builder.source.get_node(rel)
                if node is None:
                    continue
                frag = renderer.render(node, include_datapath=True)
                patches.append({"id": rel, "html": frag})
        return patches


if __name__ == "__main__":
    app = WsLiveApp()
    key = next(iter(app.pages))
    print(app.page(key))
