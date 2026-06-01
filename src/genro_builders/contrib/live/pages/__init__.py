# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Demo pages — auto-discovered from this folder.

MAGIC (intentional, documented): this package scans its own folder at
import time. Every module here that exposes a class named ``Demo`` (a
subclass of ``InteractiveDemo``) is registered automatically — no central
registry to edit. To add a demo, drop a new ``<key>.py`` in this folder
with:

    DEMO_TITLE = "Human-readable title"     # shown in the menu

    class Demo(InteractiveDemo):
        def main(self, root):
            ...

The module file name (without extension) becomes the demo's key (its URL
slug and menu id). ``discover()`` returns ``{key: (title, Demo)}`` sorted
by key. This deliberately uses dynamic import (``pkgutil`` +
``importlib``) — the convenience of "drop a file, it appears" is worth the
small departure from the project's no-magic default, and this docstring is
the contract that makes it legible.
"""

from __future__ import annotations

import importlib
import pkgutil
from typing import Any

from ..interactive_demo import InteractiveDemo


def discover() -> dict[str, tuple[str, type[InteractiveDemo]]]:
    """Scan this package and return ``{key: (title, Demo class)}``.

    ``key`` is the module name. A module qualifies when it exposes a
    ``Demo`` attribute that is an ``InteractiveDemo`` subclass; its title
    is the module's ``DEMO_TITLE`` (falling back to ``key``).
    """
    found: dict[str, tuple[str, type[InteractiveDemo]]] = {}
    for info in pkgutil.iter_modules(__path__):
        module = importlib.import_module(f"{__name__}.{info.name}")
        demo: Any = getattr(module, "Demo", None)
        if isinstance(demo, type) and issubclass(demo, InteractiveDemo):
            title = getattr(module, "DEMO_TITLE", info.name)
            found[info.name] = (title, demo)
    return dict(sorted(found.items()))
