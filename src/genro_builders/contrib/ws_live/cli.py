# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""``genro-ws-live`` — start the ws_live POC server.

Wires an ``AsgiServer`` with a single ``WsLiveApp`` mounted under the
``ws_live`` prefix and runs it. A page is served at
``http://<host>:<port>/ws_live/page/<key>`` (e.g. ``.../page/colorpicker``);
the first render arrives server-side, later mutations travel over the
WebSocket.
"""

from __future__ import annotations

import argparse
import webbrowser

from .app import WsLiveApp

MOUNT_NAME = "ws_live"


def main() -> None:
    """Entry point for the ``genro-ws-live`` console script."""
    parser = argparse.ArgumentParser(
        prog="genro-ws-live",
        description="Serve the genro-builders ws_live POC.",
    )
    parser.add_argument(
        "--host", default="localhost", help="Bind host (default: localhost)",
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Bind port (default: 8000)",
    )
    parser.add_argument(
        "--page", default="colorpicker", help="Page to open (default: colorpicker)",
    )
    parser.add_argument(
        "--open", action="store_true",
        help="Open the page in the default browser after start.",
    )
    args = parser.parse_args()

    from genro_asgi import AsgiServer

    server = AsgiServer(host=args.host, port=args.port)
    server.mount(MOUNT_NAME, WsLiveApp())

    url = f"http://{args.host}:{args.port}/{MOUNT_NAME}/page/{args.page}"
    print(f"genro-ws-live serving on {url}")
    print("Press Ctrl+C to stop.")

    if args.open:
        webbrowser.open(url)

    server.run()


if __name__ == "__main__":
    main()
