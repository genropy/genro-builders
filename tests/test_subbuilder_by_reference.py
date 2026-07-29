# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Sub-builder resolved from a parameter reference (``kwarg:attr``).

``_meta['subbuilder']`` has two forms. Without a colon it names a
registered dialect (the historical path, ``"svg"``). With a colon —
``"app:grammar"`` — the grammar class comes from the CALL SITE: the
recipe passes an object as ``app`` and its ``grammar`` attribute governs
the subtree, exactly like ``<svg>`` inside HTML but with the dialect
chosen by the recipe. The core fabricates the builder class from the
grammar mixin once (cached per grammar class), the instance is cached
per host, and the host's datastore cascades across the boundary. The
kwarg left unset means no switch: the node keeps the host dialect and,
transparent to containment, does not police children — a tag unknown to
the host grammar raises. All authoring errors raise at the recipe line.
"""
from __future__ import annotations

import pytest

from genro_builders.builder import BuilderBase, element


class ShopGrammar:
    """Grammar mixin: a shop catalog (no builder machinery of its own)."""

    @element(sub_tags="product")
    def catalog(self, title=None): ...

    @element()
    def product(self, sku=None, price=None): ...


class ExtendedShopGrammar(ShopGrammar):
    """Grammar composed by plain inheritance: widens catalog, adds discount."""

    @element(sub_tags="product,discount")
    def catalog(self, title=None): ...

    @element()
    def discount(self, percent=None): ...


class ShopApp:
    grammar = ShopGrammar


class BankApp:
    grammar = ExtendedShopGrammar


class NoGrammarApp:
    """Missing the declared attribute."""


class BadGrammarApp:
    grammar = "not-a-class"


class EmptyGrammar:
    """A class contributing no grammar elements."""


class EmptyApp:
    grammar = EmptyGrammar


class AppsHost(BuilderBase):
    """Host dialect: ``application`` mounts the grammar its ``app`` carries."""

    @element(sub_tags="application")
    def apps(self, **kwargs): ...

    @element(_meta={"subbuilder": "app:grammar"})
    def application(self, code=None, app=None): ...


def _page(main_fn, setup_fn=None):
    class Page(AppsHost):
        def main(self, root):
            main_fn(root)

    if setup_fn is not None:
        Page.setup = lambda self, data: setup_fn(data)
    page = Page()
    page.create()
    return page


def test_switch_by_reference_children_follow_the_referenced_grammar():
    def main(root):
        app = root.apps().application(code="shop", app=ShopApp)
        app.catalog(title="Summer").product(sku="S1", price=10)

    out = _page(main).render(target=False)
    assert '<catalog title="Summer">' in out
    assert '<product sku="S1" price="10">' in out


def test_disallowed_child_raises_at_the_recipe_line():
    def main(root):
        app = root.apps().application(code="shop", app=ShopApp)
        app.catalog().spam()

    with pytest.raises(AttributeError, match="spam"):
        _page(main)


def test_inheritance_composed_grammar():
    def main(root):
        app = root.apps().application(code="bank", app=BankApp)
        catalog = app.catalog(title="Rates")
        catalog.product(sku="P1")
        catalog.discount(percent=5)

    out = _page(main).render(target=False)
    assert '<discount percent="5">' in out
    assert '<product sku="P1">' in out


def test_same_grammar_class_shares_one_subbuilder_instance():
    captured = {}

    def main(root):
        apps = root.apps()
        a1 = apps.application(code="one", app=ShopApp)
        a2 = apps.application(code="two", app=ShopApp)
        captured["same"] = a1._builder is a2._builder

    _page(main)
    assert captured["same"] is True


def test_fabricated_class_is_cached_per_grammar_class():
    def main(root):
        root.apps().application(code="shop", app=ShopApp)

    _page(main)
    first = BuilderBase._grammar_builders[ShopGrammar]
    _page(main)
    assert BuilderBase._grammar_builders[ShopGrammar] is first


def test_datastore_is_shared_across_the_boundary():
    def setup(data):
        data["current_sku"] = "ABC"

    def main(root):
        app = root.apps().application(code="shop", app=ShopApp)
        app.catalog().product(sku="^current_sku")

    out = _page(main, setup).render(target=False)
    assert '<product sku="ABC">' in out


def test_kwarg_missing_the_declared_attribute_raises():
    def main(root):
        root.apps().application(code="x", app=NoGrammarApp())

    with pytest.raises(ValueError, match="no attribute 'grammar'"):
        _page(main)


def test_attribute_not_a_class_raises():
    def main(root):
        root.apps().application(code="x", app=BadGrammarApp())

    with pytest.raises(ValueError, match="must be a class"):
        _page(main)


def test_grammar_with_no_declared_elements_raises():
    def main(root):
        root.apps().application(code="x", app=EmptyApp())

    with pytest.raises(ValueError, match="declares no grammar elements"):
        _page(main)


def test_kwarg_absent_means_no_switch():
    """Kwarg absent: no dialect switch — a child tag unknown to the host grammar raises."""

    def main(root):
        app = root.apps().application(code="bare")
        app.catalog()

    with pytest.raises(AttributeError, match="catalog"):
        _page(main)


def test_registry_name_form_is_unchanged():
    from genro_builders.contrib.html import HtmlBuilder

    class Page(HtmlBuilder):
        def main(self, root):
            root.body().svg(width=10).rect(x=1, y=1, width=2, height=2)

    page = Page()
    page.create()
    out = page.render(target=False)
    assert '<svg width="10">' in out
    assert "<rect" in out
