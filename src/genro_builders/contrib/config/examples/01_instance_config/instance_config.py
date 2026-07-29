# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""01 — Instance configuration: recipe, dump, four-layer reads. See readme.md."""
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


class InstanceConfig(ConfigBuilder):
    """The recipe: what a ``config.py`` of an instance would define."""

    def main(self, root):
        c = root.configuration()
        c.server(host="localhost")
        apps = c.applications()
        shop = apps.application(code="shop", app=ShopApp)
        shop.catalog(title="Summer sale").product(sku="S1", price=10)
        apps.application(code="crm", app=CrmApp).pipeline()


class Application:
    """App-side delegation: prefix your own code, bounce to the parent."""

    def __init__(self, code, server):
        self.code = code
        self.server = server

    def config(self, path, default=None):
        return self.server.config(f"applications.{self.code}.{path}", default=default)


class Server:
    """The config door of the server IS the handler."""

    def __init__(self, handler):
        self.config = handler


if __name__ == "__main__":
    config = ConfigHandler(InstanceConfig)
    config.builder.set_render_target("output.xml")
    config.builder.render(pretty=True)

    server = Server(config)
    shop = Application("shop", server)
    crm = Application("crm", server)
    print("written:          ", config("server.host"))
    print("signature default:", config("server.port"))
    print("call-site default:", config("server.workers", default=4))
    print("delegated read:   ", shop.config("catalog.title"))
    print("mounted default:  ", crm.config("pipeline.stages"))
    try:
        config("server.tls")
    except KeyError as exc:
        print("noisy error:      ", exc)
    print(config.builder.rendered_target)
