# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""WsLiveApp — server-side reactive SPA on the legacy page cycle.

The cycle (the GenroPy one, refounded):

1. HTTP serves the SAME startup page for every page key: resource
   links, an empty ``mainWindow``, the inline GenroClient.
2. The client connects the websocket and calls ``main``: the server
   prepares the live page (one builder + handler per connection, the
   ``WsTargetWrapper`` as render target) and returns the rendered HTML
   of the main div — the content's first paint.
3. ``mutate`` applies a data change inside ``handler.live()``; the
   flush delivers the patch batch to the wrapper (optimizer, component
   lift and transparent-reader rules included), and the response
   carries it. The client applies each patch by id.

HTTP and WebSocket are distinct connections: the GET is stateless (the
skeleton is a constant), the live instances belong to the websocket
(``ws.state``).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from genro_asgi import AsgiApplication
from genro_asgi.request import get_current_request
from genro_routes import route

from genro_builders.builder import BuilderHandler

from . import pages
from .startup_page import STARTUP_HTML
from .target import WsTargetWrapper

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

    # ------------------------------------------------------------------
    # HTTP — the startup page (one fixed skeleton for every page)
    # ------------------------------------------------------------------

    @route(meta_mime_type="text/html")
    def page(self, *args: str) -> str:
        """Serve the startup skeleton. ``/<app>/page/<key>``.

        Always the same document: the page key only parameterizes the
        client bootstrap; the content arrives later over the websocket.
        """
        key = args[0] if args else next(iter(self.pages))
        title, _ = self.pages[key]
        return STARTUP_HTML % {"page": key, "title": title}

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
    # WSX — the live page (per-connection, prepared on ``main``)
    # ------------------------------------------------------------------

    def _prepare(self, key: str) -> Any:
        """Instantiate and mount the page ``key`` on its own handler.

        One builder per page per connection, the ``WsTargetWrapper`` as
        its render target (the wrapper rides on the builder as
        ``ws_target``). ``activate`` renders once — the full content
        lands in the wrapper — and arms the data subscribe.
        """
        title, page_class = self.pages[key]
        builder = page_class()
        builder.ws_target = WsTargetWrapper()
        builder.set_render_target(builder.ws_target)
        handler = BuilderHandler(application=self)
        handler.add_builder(builder)
        handler.activate()
        return builder

    def _live_builder(self, key: str) -> Any:
        """Return the connection's live builder for ``key`` (lazy)."""
        request = get_current_request()
        ws = request.websocket
        if "pages" not in ws.state:
            ws.state.pages = {}
        registry = ws.state.pages
        builder = registry.get(key)
        if builder is None:
            builder = self._prepare(key)
            registry[key] = builder
        return builder

    @route()
    def main(self, page: str = "") -> dict[str, Any]:
        """First client call: the rendered HTML of the main div."""
        key = page or next(iter(self.pages))
        builder = self._live_builder(key)
        return {"html": builder.ws_target.last_full}

    @route()
    def mutate(self, page: str = "", path: str = "", value: Any = None) -> dict[str, Any]:
        """Apply a data mutation to the live page; respond with the patches.

        The write runs inside ``handler.live()``: the flush delivers the
        batch to the wrapper — optimizer, component lift and
        transparent-reader rules included — and the response drains it.
        The client applies each ``{id, op, html}`` by id.
        """
        builder = self._live_builder(page)
        handler = builder.handler
        with handler.live():
            handler.data.set_item(path, value)
        return {"ok": True, "patches": builder.ws_target.take()}


if __name__ == "__main__":
    app = WsLiveApp()
    key = next(iter(app.pages))
    print(app.page(key))
