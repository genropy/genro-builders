# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""WsLiveApp — server-side reactive SPA on the legacy page cycle.

The cycle (the GenroPy one, refounded — see
roadmap/application-registry.md):

1. HTTP serves the SAME startup page for every page key: resource
   links, an empty ``mainWindow``, the inline GenroClient.
2. The client connects the websocket and calls ``main``: the server
   prepares the live page (one builder + handler per connection, the
   ``WsTargetWrapper`` bound to the connection) and returns the
   rendered HTML of the main div — the content's first paint.
3. Patches travel ONE road: every ``live()`` flush — a client mutate,
   a server timer, anything — is PUSHED over the websocket by the
   wrapper. ``mutate`` responds only the outcome.

The sync world (builders, handlers, live sections) runs in worker
threads (``asyncio.to_thread``); the async routes capture the event
loop and the connection so the wrapper can bridge back
(``run_coroutine_threadsafe``). A page declaring ``live_interval``
gets a server-side ticker: its ``tick()`` runs inside ``live()`` and
the resulting patches reach the browser with no client request —
server-initiated reactivity end to end.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from genro_asgi import AsgiApplication
from genro_asgi.request import get_current_request
from genro_asgi.websocket import WebSocketState
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
        self.loop: asyncio.AbstractEventLoop | None = None

    def on_startup(self) -> None:
        """Capture the server's event loop (lifespan runs inside it).

        The sync world — routes in worker threads, live() flushes —
        bridges back to the connection through this reference
        (``run_coroutine_threadsafe`` in the wrapper and for the
        tickers).
        """
        self.loop = asyncio.get_running_loop()

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

    def _prepare(self, key: str, ws: Any) -> Any:
        """Instantiate and mount the page ``key`` on its own handler.

        One builder per page per connection; the ``WsTargetWrapper``
        (riding on the builder as ``ws_target``) is bound to the
        connection so every flush pushes its patches. ``activate``
        renders once — the full content lands in the wrapper — and arms
        the data subscribe.
        """
        title, page_class = self.pages[key]
        builder = page_class()
        builder.ws_target = WsTargetWrapper(page_key=key)
        builder.ws_target.bind(ws, self.loop)
        builder.set_render_target(builder.ws_target)
        handler = BuilderHandler(application=self)
        handler.add_builder(builder)
        handler.activate()
        return builder

    def _live_builder(self, key: str, ws: Any) -> Any:
        """Return the connection's live builder for ``key`` (lazy)."""
        if "pages" not in ws.state:
            ws.state.pages = {}
        registry = ws.state.pages
        builder = registry.get(key)
        if builder is None:
            builder = self._prepare(key, ws)
            registry[key] = builder
            interval = getattr(builder, "live_interval", None)
            if interval:
                builder._ticker_future = asyncio.run_coroutine_threadsafe(
                    self._ticker(ws, builder, interval), self.loop,
                )
        return builder

    @route()
    def main(self, page: str = "") -> dict[str, Any]:
        """First client call: the rendered HTML of the main div."""
        key = page or next(iter(self.pages))
        ws = get_current_request().websocket
        builder = self._live_builder(key, ws)
        return {"html": builder.ws_target.last_full}

    @route()
    def mutate(
        self, page: str = "", path: str = "", value: Any = None,
    ) -> dict[str, Any]:
        """Apply a data mutation to the live page.

        The write runs inside ``handler.live()``; the flush pushes the
        patches over the connection (single road), so the response
        carries only the outcome.
        """
        builder = self._live_builder(page, get_current_request().websocket)
        handler = builder.handler
        with handler.live():
            handler.data.set_item(path, value)
        return {"ok": True}

    # ------------------------------------------------------------------
    # Server-initiated reactivity — the ticker
    # ------------------------------------------------------------------

    async def _ticker(self, ws: Any, builder: Any, interval: float) -> None:
        """Run the page's ``tick()`` inside ``live()`` every ``interval``.

        The patches reach the browser through the wrapper push — no
        client request involved. The ticker dies with the connection.
        """
        while ws.connection_state == WebSocketState.CONNECTED:
            await asyncio.sleep(interval)
            if ws.connection_state != WebSocketState.CONNECTED:
                break
            await asyncio.to_thread(self._tick, builder)

    def _tick(self, builder: Any) -> None:
        with builder.handler.live():
            builder.tick()


if __name__ == "__main__":
    app = WsLiveApp()
    key = next(iter(app.pages))
    print(app.page(key))
