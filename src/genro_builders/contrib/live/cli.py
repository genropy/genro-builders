# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""``genro-live`` — start the live HTML demo server.

Wires an ``AsgiServer`` with a single ``LiveDemoApp`` mounted under
the ``live`` prefix and runs it via ``server.run()``. The browser side
(SPA shell + REPL) is served at ``http://<host>:<port>/live/index``.
"""

from __future__ import annotations

import argparse
import webbrowser

from .app import LiveDemoApp

MOUNT_NAME = "live"


def main() -> None:
    """Entry point for the ``genro-live`` console script."""
    parser = argparse.ArgumentParser(
        prog="genro-live",
        description="Serve the genro-builders live HTML demo.",
    )
    parser.add_argument(
        "--host", default="localhost", help="Bind host (default: localhost)",
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Bind port (default: 8000)",
    )
    parser.add_argument(
        "--open", action="store_true",
        help="Open the demo in the default browser after start.",
    )
    args = parser.parse_args()

    from genro_asgi import AsgiServer

    server = AsgiServer(host=args.host, port=args.port)
    server.mount(MOUNT_NAME, LiveDemoApp())

    url = f"http://{args.host}:{args.port}/{MOUNT_NAME}/index"
    print(f"genro-live serving on {url}")
    print("Open the URL in a browser, then type commands in the REPL panel.")
    print("Press Ctrl+C to stop.")

    if args.open:
        webbrowser.open(url)

    # AsgiServer.run() drives uvicorn itself (uvicorn.run(self)), reading
    # host/port from the config seeded by the AsgiServer(...) call above.
    server.run()


if __name__ == "__main__":
    main()
