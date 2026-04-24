# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""11 — Live REPL: real-time HTML editing via contrib/live.

What you learn:
    - enable_remote(): start a socket server on a running ReactiveManager
    - genro-live connect: open a Python REPL to manipulate source and data
    - Changes in the REPL update the HTML file instantly
    - Data and CSS from external files

Prerequisites: 08_reactive_basics, contrib/live installed

Setup:
    Terminal 1: python 11_live_repl.py          # starts the app + server
    Terminal 2: genro-live connect livepage      # opens REPL

Usage:
    python 11_live_repl.py
"""
from __future__ import annotations

import signal
from pathlib import Path

from genro_bag import Bag
from genro_bag.resolvers import FileResolver

from genro_builders.contrib.html import HtmlBuilder
from genro_builders.contrib.live import enable_remote
from genro_builders.manager import ReactiveManager
from genro_builders.render_target import FileRenderTarget

HERE = Path(__file__).parent
OUTPUT = HERE / "11_live_repl.html"


class LivePage(ReactiveManager):
    """A reactive page that writes HTML on every data change."""

    def on_init(self):
        self.page = self.register_builder("page", HtmlBuilder)
        self.run(subscribe=True)
        self.set_render_target("html",
            target=FileRenderTarget(OUTPUT),
        )

    def main(self, source):
        head = source.head()
        head.title("^title")
        # FileResolver: pull model — content loaded on demand at render time
        head.style(FileResolver("style.css", base_path=str(HERE)))

        body = source.body()
        body.h1("^title")
        body.p("^message")


app = LivePage()
app.local_store("page").fill_from(
    Bag.from_json((HERE / "data.json").read_text()),
)
app.page.build()
# Initial render to file
OUTPUT.write_text(app.page.render())

server = enable_remote(app, name="livepage")

print(f"Live session 'livepage' on port {server.port}")
print(f"HTML output: {OUTPUT}")
print()
print("Connect from another terminal:")
print("  genro-live connect livepage")
print()
print("Then try:")
print('  data["page.title"] = "Hello from REPL!"')
print('  data["page.message"] = "This updates the HTML file instantly."')
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
