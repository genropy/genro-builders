# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Live demo — interactive HTML builder REPL driven over WebSocket.

A single-page app served by ``genro-asgi`` that hosts several
``InteractiveDemo`` pages (auto-discovered from ``pages/``) and exposes a
Python REPL over WSX. Snippets typed in the page's editor run inside
``handler.live()`` on the current demo; the rendered HTML is written to
``out.html`` and shown in an iframe.

Useful as both a developer playground and an end-to-end integration test
of ``genro-builders`` + ``genro-asgi`` + ``genro-routes`` + ``WsxHandler``
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
from .interactive_demo import InteractiveDemo

__all__ = ["InteractiveDemo", "LiveDemoApp"]
