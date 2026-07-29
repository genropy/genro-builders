# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for the ``contrib/config`` dialect grammar.

The layout the dialect guarantees: stable, hand-writable paths.
``configuration`` is the single root element; ``server`` and
``applications`` take their tag as label (singleton sections); each
``application`` is labelled by its ``code`` (explicit collection); the
``app=`` value mounts its own grammar under the node (subbuilder by
reference).
"""
from __future__ import annotations

import pytest
from genro_bag.resolver import BagSyncResolver

from genro_builders.builder import element
from genro_builders.contrib.config import ConfigBuilder


class _Env(BagSyncResolver):
    """Returns a value handed at construction time."""

    class_kwargs = dict(BagSyncResolver.class_kwargs)

    def load(self):
        return self._kw.get("payload")


class ShopGrammar:
    """Grammar mixin an application brings to the mount."""

    @element(sub_tags="product", node_label="catalog")
    def catalog(self, title: str = "Untitled"): ...

    @element(parent_tags="catalog")
    def product(self, sku: str = None, price: int = None): ...


class CrmGrammar:
    """A second, unrelated application grammar."""

    @element(node_label="pipeline")
    def pipeline(self, stages: int = 3): ...


class ShopApp:
    grammar = ShopGrammar


class CrmApp:
    grammar = CrmGrammar


def _page(main_fn):
    class Page(ConfigBuilder):
        def main(self, root):
            main_fn(root)

    page = Page()
    page.create()
    return page


def test_root_element_stable_label():
    page = _page(lambda root: root.configuration())
    assert [n.label for n in page.source] == ["configuration"]


def test_singleton_sections_labelled_by_tag():
    def main(root):
        c = root.configuration()
        c.server(host="localhost")
        c.applications()

    page = _page(main)
    root_el = page.source.get_node("configuration")
    assert [n.label for n in root_el.value] == ["server", "applications"]


def test_second_server_raises():
    def main(root):
        c = root.configuration()
        c.server(host="a")
        c.server(host="b")

    with pytest.raises(ValueError, match="at most once"):
        _page(main)


def test_applications_labelled_by_code():
    def main(root):
        apps = root.configuration().applications()
        apps.application(code="shop", app=ShopApp)
        apps.application(code="bank", app=CrmApp)

    page = _page(main)
    apps = page.source.get_node("configuration.applications")
    assert [n.label for n in apps.value] == ["shop", "bank"]


def test_duplicate_application_code_raises():
    def main(root):
        apps = root.configuration().applications()
        apps.application(code="shop", app=ShopApp)
        apps.application(code="shop", app=CrmApp)

    with pytest.raises(ValueError, match="duplicate collection key"):
        _page(main)


def test_application_without_code_raises():
    def main(root):
        root.configuration().applications().application(app=ShopApp)

    with pytest.raises(ValueError, match="code"):
        _page(main)


def test_mount_switches_to_app_grammar():
    def main(root):
        apps = root.configuration().applications()
        shop = apps.application(code="shop", app=ShopApp)
        shop.catalog(title="Summer").product(sku="S1", price=10)
        apps.application(code="crm", app=CrmApp).pipeline(stages=5)

    page = _page(main)
    catalog = page.source.get_node("configuration.applications.shop.catalog")
    assert catalog.attr.get("title") == "Summer"
    pipeline = page.source.get_node("configuration.applications.crm.pipeline")
    assert pipeline.attr.get("stages") == 5


def test_wrong_child_in_mount_raises_at_recipe_line():
    def main(root):
        shop = root.configuration().applications().application(code="shop", app=ShopApp)
        shop.spam()

    with pytest.raises(AttributeError, match="spam"):
        _page(main)


def test_server_outside_configuration_raises():
    with pytest.raises(ValueError):
        _page(lambda root: root.server(host="x"))


def test_application_outside_applications_raises():
    def main(root):
        root.configuration().application(code="shop", app=ShopApp)

    with pytest.raises(ValueError):
        _page(main)


def test_unknown_attribute_raises():
    def main(root):
        root.configuration().server(hots="typo")

    with pytest.raises(ValueError, match="hots"):
        _page(main)


def test_wrong_type_raises():
    def main(root):
        root.configuration().server(port="8000")

    with pytest.raises(ValueError, match="expected"):
        _page(main)


def test_resolver_as_attribute_builds_and_reads():
    def main(root):
        root.configuration().server(host=_Env(payload="from-env"))

    page = _page(main)
    assert page.source["configuration.server?host"] == "from-env"


def test_render_xml():
    def main(root):
        c = root.configuration()
        c.server(host="localhost", port=9000)

    out = _page(main).render(target=False)
    assert '<server host="localhost" port="9000"' in out
    assert "<configuration>" in out
