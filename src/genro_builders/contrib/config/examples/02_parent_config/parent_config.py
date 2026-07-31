# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""02 — Parent configuration: layering executed recipes. See readme.md."""
from __future__ import annotations

from genro_builders.builder import element
from genro_builders.contrib.config import ConfigBuilder, ConfigHandler


class ShopGrammar:
    """Grammar the shop application brings to its mount point."""

    @element(sub_tags="product", node_label="catalog")
    def catalog(self, title: str = "Untitled"): ...

    @element(parent_tags="catalog")
    def product(self, sku: str = None, price: int = None): ...


class CrmGrammar:
    """A second application, a different vocabulary."""

    @element(node_label="pipeline")
    def pipeline(self, stages: int = 3): ...


class ShopApp:
    grammar = ShopGrammar


class CrmApp:
    grammar = CrmGrammar


class DefaultsConfig(ConfigBuilder):
    """The base layer: what a framework's ``defaults/config.py`` would ship."""

    def main(self, root):
        c = root.configuration()
        c.server(host="localhost", port=9000)
        apps = c.applications()
        apps.application(code="shop", app=ShopApp).catalog(title="Base catalog")


class InstanceConfig(ConfigBuilder):
    """The instance layer: rewrites one value, adds one application."""

    def main(self, root):
        c = root.configuration()
        c.server(host="prod.example.com")
        c.applications().application(code="crm", app=CrmApp).pipeline()


if __name__ == "__main__":
    config = ConfigHandler(InstanceConfig, parents=[DefaultsConfig])
    config.builder.set_render_target("output.xml")
    config.builder.render(pretty=True)

    print("instance wins:    ", config("server.host"))
    print("base inherited:   ", config("server.port"))
    print("base-only subtree:", config("applications.shop.catalog.title"))
    print("instance addition:", config("applications.crm.pipeline.stages"))
    print(config.builder.rendered_target)
