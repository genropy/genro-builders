# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Live demo — interactive HTML builder driven over WebSocket.

A single-page app served by ``genro-asgi`` that hosts an
``HtmlBuilderHandler`` and exposes its mutation API over WSX.
Commands typed in the page's REPL panel travel as WebSocket messages
through ``WsxHandler``, are dispatched to ``@route()`` methods on
``LiveDemoApp``, and the resulting HTML is sent back and shown in the
top panel.

Useful as both a developer demo and an end-to-end integration test of
``genro-builders`` + ``genro-asgi`` + ``genro-routes`` + ``WsxHandler``
working together.

The package requires the ``live`` extra::

    pip install "genro-builders[live]"

Then start the server::

    genro-live

Example::

    from genro_builders.contrib.live import LiveDemoApp
    from genro_asgi import AsgiServer

    server = AsgiServer()
    server.mount("live", LiveDemoApp())  # mount(name, app)
    server.run()                         # drives uvicorn internally
"""

from __future__ import annotations

from .app import LiveDemoApp
from .demo_page import DemoPage

__all__ = ["DemoPage", "LiveDemoApp"]
