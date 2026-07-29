# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Config contrib — ConfigBuilder and ConfigHandler.

The recipe subclasses ``ConfigBuilder`` and builds the tree; the
runtime reads it through a ``ConfigHandler``.

Example::

    from genro_builders.contrib.config import ConfigBuilder, ConfigHandler

    class InstanceConfig(ConfigBuilder):
        def main(self, root):
            c = root.configuration()
            c.server(host="localhost")
            c.applications().application(code="shop", app=ShopApp)

    config = ConfigHandler(InstanceConfig)
    config("server.host")   # "localhost"  (written)
    config("server.port")   # 8000         (signature default)
    config("applications.shop.title", default="x")  # "x" (call-site default)
"""

from __future__ import annotations

from .config_builder import ConfigBuilder
from .handler import ConfigHandler

__all__ = ["ConfigBuilder", "ConfigHandler"]
