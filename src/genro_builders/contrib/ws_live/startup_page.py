# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""The startup page — one fixed skeleton for EVERY page (legacy model).

The HTTP route serves this same document whatever the page: resource
links, an empty ``mainWindow`` and the inline instantiation of the
GenroClient. The page CONTENT never travels over HTTP: the client opens
the websocket and asks ``main`` for the rendered HTML of the main div.
"""
from __future__ import annotations

STARTUP_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>%(title)s</title>
<link rel="stylesheet" href="../static?file=ws_live.css">
<script src="../static?file=genro.js"></script>
<script>var genro = new GenroClient({page: "%(page)s"});</script>
</head>
<body data-gnr-status="loading">
<div id="mainWindow" class="waiting"></div>
</body>
</html>
"""
