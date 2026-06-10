# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""ws_live pages — auto-discovered from this folder.

MAGIC (intentional, documented): this package scans its own folder at
call time. Every module here that exposes a class named ``Page`` (a
subclass of ``WsLivePage``) is registered automatically — no central
registry to edit. To add a page, drop a new ``<key>.py`` in this folder
with:

    PAGE_TITLE = "Human-readable title"

    class Page(WsLivePage):
        def main(self, root):
            ...   # CONTENT only: the shell is the fixed startup page

The module file name (without extension) becomes the page's key (its URL
slug). ``discover()`` returns ``{key: (title, Page)}`` sorted by key.
"""

from __future__ import annotations

import importlib
import pkgutil
from typing import Any

from ..base_page import WsLivePage


def discover() -> dict[str, tuple[str, type[WsLivePage]]]:
    """Scan this package and return ``{key: (title, Page class)}``.

    ``key`` is the module name. A module qualifies when it exposes a
    ``Page`` attribute that is a ``WsLivePage`` subclass; its title is the
    module's ``PAGE_TITLE`` (falling back to ``key``).
    """
    found: dict[str, tuple[str, type[WsLivePage]]] = {}
    for info in pkgutil.iter_modules(__path__):
        module = importlib.import_module(f"{__name__}.{info.name}")
        page: Any = getattr(module, "Page", None)
        if isinstance(page, type) and issubclass(page, WsLivePage):
            title = getattr(module, "PAGE_TITLE", info.name)
            found[info.name] = (title, page)
    return dict(sorted(found.items()))
