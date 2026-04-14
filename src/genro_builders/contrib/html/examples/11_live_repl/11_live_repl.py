# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""11 — Live REPL: real-time HTML editing via contrib/live.

What you learn:
    - enable_remote(): start a socket server on a running ReactiveManager
    - genro-live connect: open a Python REPL to manipulate source and data
    - Changes in the REPL update the HTML file instantly
    - The browser (with live-reload) shows changes in real time

Prerequisites: 08_reactive_basics, contrib/live installed

Setup:
    Terminal 1: python 11_live_repl.py          # starts the app + server
    Terminal 2: genro-live connect livepage      # opens REPL

    For auto-reload in the browser, use any live-reload tool:
        npx live-server --watch=11_live_repl.html
    or:
        python -m http.server  (then manually refresh)

REPL commands:
    source.h2("New heading")          # add an element to source
    data["title"] = "Updated Title"   # change reactive data
    remote.builders()                 # list builder names
    /help                             # REPL help
    /quit                             # disconnect

Usage:
    python 11_live_repl.py
"""
from __future__ import annotations

import signal
from pathlib import Path

from genro_builders.contrib.html import HtmlBuilder
from genro_builders.contrib.live import enable_remote
from genro_builders.manager import ReactiveManager

OUTPUT = Path(__file__).with_suffix(".html")


class LivePage(ReactiveManager):
    """A reactive page that writes HTML on every data change."""

    def __init__(self):
        self.page = self.set_builder("page", HtmlBuilder)
        self.run(subscribe=True)
        # Re-write HTML on every data change (side effect via subscribe)
        self.reactive_store.subscribe(
            "html_writer", any=lambda **kw: self._write_html(),
        )

    def store(self, data):
        data["title"] = "Live Page"
        data["message"] = "Edit me from the REPL!"

    def main(self, source):
        head = source.head()
        head.title("^title")
        head.style("""
            body { font-family: sans-serif; max-width: 600px; margin: 2em auto; }
            h1 { color: #2563eb; }
        """)

        body = source.body()
        body.h1("^title")
        body.p("^message")

    def _write_html(self):
        """Write current render to file."""
        html = self.page.render()
        OUTPUT.write_text(html)


app = LivePage()
app._write_html()  # initial write

# Start remote server — REPL clients connect to this
server = enable_remote(app, name="livepage")

print(f"Live session 'livepage' on port {server.port}")
print(f"HTML output: {OUTPUT}")
print()
print("Connect from another terminal:")
print("  genro-live connect livepage")
print()
print("Then try:")
print('  data["title"] = "Hello from REPL!"')
print('  data["message"] = "This updates the HTML file instantly."')
print()
print("Press Ctrl+C to stop.")

try:
    signal.pause()
except KeyboardInterrupt:
    print("\nStopping...")
finally:
    server.stop()
    from genro_builders.contrib.live._registry import LiveRegistry
    LiveRegistry().unregister("livepage")
    print("Done.")
