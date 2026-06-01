# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""DemoPage — initial document shown by the live demo.

A minimal ``HtmlBuilderHandler`` with a few id'd nodes that the user
can target from the REPL. Replace it (or subclass and override
``main``) to drive the demo against a different document.
"""

from __future__ import annotations

from ..html import HtmlBuilderHandler


class DemoPage(HtmlBuilderHandler):
    """Initial document: a heading and a paragraph, both bound to data."""

    def main(self, root):
        body = root.body(datapath="page", node_id="body")
        body.h1("^.title", node_id="h1")
        body.p("^.message", node_id="msg")
