# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""WsTargetWrapper — the connection-bound render destination.

The single road of the patches (application-registry.md §3): every
``live()`` flush — triggered by a client mutate, a server timer,
anything — delivers its batch to this wrapper, and the wrapper PUSHES
it over the websocket. The mutate response carries only the outcome;
patches always travel as pushed messages, so server-initiated
reactivity rides the same wire as request-driven one.

The flush runs in a worker thread (sync world); the websocket sends
are coroutines on the event loop. The wrapper is bound to ``(ws,
loop)`` at page preparation and bridges with
``asyncio.run_coroutine_threadsafe``.
"""
from __future__ import annotations

import asyncio
from typing import Any, ClassVar

from genro_asgi.wsx.protocol import build_wsx_response

from genro_builders.builder import TargetWrapper


class WsTargetWrapper(TargetWrapper):
    """Pushes patch batches over the bound websocket connection."""

    accepts_partial = True
    render_opts: ClassVar[dict[str, Any]] = {"include_datapath": True}

    def __init__(self, page_key: str = "") -> None:
        self.page_key = page_key
        self.last_full: str | None = None
        self._ws: Any = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._counter = 0

    def bind(self, ws: Any, loop: asyncio.AbstractEventLoop) -> None:
        """Bind the destination to its connection and event loop."""
        self._ws = ws
        self._loop = loop

    def full(self, document: Any) -> None:
        self.last_full = document

    def partial(self, patches: list[dict[str, Any]]) -> None:
        """Push the batch over the connection (routing key included)."""
        if self._ws is None or self._loop is None:
            raise RuntimeError("WsTargetWrapper.partial() before bind()")
        if not patches:
            return
        self._counter += 1
        message = build_wsx_response(
            id=f"push_{self._counter}",
            status=200,
            data={"page": self.page_key, "patches": patches},
        )
        asyncio.run_coroutine_threadsafe(
            self._ws.send_text(message), self._loop,
        )
