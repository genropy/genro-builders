# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""10 — Subbuilder by reference: the recipe chooses the grammar. See readme.md."""
from __future__ import annotations

from genro_builders.builder import BuilderBase, element


class ShopGrammar:
    """Grammar mixin the recipe mounts: a shop catalog."""

    @element(sub_tags="product")
    def catalog(self, title=None): ...

    @element()
    def product(self, sku=None, price=None): ...


class ShopApp:
    """The object the recipe passes: it CARRIES its grammar."""

    grammar = ShopGrammar


class AppsBuilder(BuilderBase):
    """Host dialect: ``application`` mounts the grammar its ``app`` carries.

    ``_meta={"subbuilder": "app:grammar"}`` is a parameter reference: at
    the call site the value of the ``app`` kwarg supplies the ``grammar``
    class that governs the subtree — like ``<svg>`` inside HTML, but with
    the dialect chosen by the recipe.
    """

    _default_render_mode = "xml"

    @element(sub_tags="application")
    def apps(self, **kwargs): ...

    @element(_meta={"subbuilder": "app:grammar"})
    def application(self, code=None, app=None): ...


class ShopDocument(AppsBuilder):
    def main(self, root):
        app = root.apps().application(code="shop", app=ShopApp)
        # From here down the active grammar is ShopGrammar's.
        catalog = app.catalog(title="Summer sale")
        catalog.product(sku="S1", price=10)
        catalog.product(sku="S2", price=25)


if __name__ == "__main__":
    page = ShopDocument()
    page.set_render_target("output.xml")
    page.create()
    page.render(pretty=True)
    print(page.rendered_target)
