# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for ``ConfigHandler`` — the callable read door.

The four-layer stack, in order: written value (resolvers transparent)
-> signature default (read-time, from the addressed node's builder) ->
call-site ``default=`` -> noisy ``KeyError`` with the full path. Plus
the three construction sources (config.py path / builder class /
builder instance) and the documented application-side delegation.
"""
from __future__ import annotations

import re
import textwrap

import pytest
from genro_bag.resolver import BagSyncResolver

from genro_builders.builder import element
from genro_builders.contrib.config import ConfigBuilder, ConfigHandler


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


class ShopApp:
    grammar = ShopGrammar


def _recipe(body):
    """A ``ConfigBuilder`` subclass whose ``main`` runs ``body(root)``."""

    class Recipe(ConfigBuilder):
        main_runs = 0

        def main(self, root):
            type(self).main_runs += 1
            body(root)

    return Recipe


def _standard_recipe():
    def body(root):
        c = root.configuration()
        c.server(host="localhost")
        shop = c.applications().application(code="shop", app=ShopApp)
        shop.catalog().product(sku="S1")

    return _recipe(body)


# --- the four layers ---------------------------------------------------


def test_layer1_written_value():
    h = ConfigHandler(_standard_recipe())
    assert h("server.host") == "localhost"


def test_layer1_resolver_value():
    def body(root):
        root.configuration().server(host=_Env(payload="s3cr3t"))

    h = ConfigHandler(_recipe(body))
    assert h("server.host") == "s3cr3t"


def test_layer2_signature_default_typed():
    h = ConfigHandler(_standard_recipe())
    value = h("server.port")
    assert value == 8000
    assert isinstance(value, int)


def test_layer2_none_default_is_absent():
    def body(root):
        root.configuration().server(port=9000)

    h = ConfigHandler(_recipe(body))
    with pytest.raises(KeyError):
        h("server.host")


def test_layer2_inside_mounted_grammar():
    h = ConfigHandler(_standard_recipe())
    assert h("applications.shop.catalog.title") == "Untitled"


def test_layer2_on_mount_envelope_via_host_grammar():
    class ThemedConfig(ConfigBuilder):
        @element(parent_tags="applications", _meta={"subbuilder": "app:grammar"})
        def application(self, code: str, app=None, theme: str = "plain"): ...

        def main(self, root):
            root.configuration().applications().application(code="shop", app=ShopApp)

    h = ConfigHandler(ThemedConfig)
    assert h("applications.shop.theme") == "plain"


def test_mount_envelope_signature_is_host_side_even_on_tag_collision():
    """The envelope's own arguments belong to the HOST grammar — no fallback."""

    class TrickyGrammar:
        @element(node_label="application")
        def application(self, theme: str = "dark"): ...

    class TrickyApp:
        grammar = TrickyGrammar

    class ThemedConfig(ConfigBuilder):
        @element(parent_tags="applications", _meta={"subbuilder": "app:grammar"})
        def application(self, code: str, app=None, theme: str = "plain"): ...

        def main(self, root):
            root.configuration().applications().application(code="x", app=TrickyApp)

    h = ConfigHandler(ThemedConfig)
    assert h("applications.x.theme") == "plain"


def test_layer2_skipped_when_node_missing():
    def body(root):
        root.configuration()

    h = ConfigHandler(_recipe(body))
    assert h("server.port", default=4242) == 4242
    with pytest.raises(KeyError):
        h("server.port")


def test_layer3_call_site_default_suppresses_error():
    h = ConfigHandler(_standard_recipe())
    assert h("applications.shop.timeout", default=30) == 30


def test_layer4_keyerror_carries_full_path():
    h = ConfigHandler(_standard_recipe())
    with pytest.raises(KeyError, match=re.escape("'server.tls'")) as exc:
        h("server.tls")
    assert "configuration.server?tls" in str(exc.value)


# --- path semantics ----------------------------------------------------


def test_single_segment_path_reads_root_attribute():
    class MyConfig(ConfigBuilder):
        @element(sub_tags="server[0:1],applications[0:1]", node_label="configuration")
        def configuration(self, title: str = None): ...

        def main(self, root):
            root.configuration(title="Prod")

    h = ConfigHandler(MyConfig)
    assert h("title") == "Prod"


def test_mount_node_own_attribute():
    h = ConfigHandler(_standard_recipe())
    assert h("applications.shop.code") == "shop"


def test_empty_path_raises():
    h = ConfigHandler(_standard_recipe())
    with pytest.raises(ValueError, match="non-empty"):
        h("")


def test_delegation_pattern():
    class Server:
        def __init__(self, handler):
            self.config = handler

    class Application:
        def __init__(self, code, server):
            self.code = code
            self.server = server

        def config(self, path, default=None):
            return self.server.config(
                f"applications.{self.code}.{path}", default=default,
            )

    def body(root):
        c = root.configuration()
        c.server(host="localhost")
        shop = c.applications().application(code="shop", app=ShopApp)
        shop.catalog(title="Summer")

    server = Server(ConfigHandler(_recipe(body)))
    app = Application("shop", server)
    assert app.config("catalog.title") == "Summer"
    assert app.config("code") == "shop"
    assert app.config("catalog.subtitle") is None  # default=None suppresses the error


# --- construction sources ----------------------------------------------


def test_handler_from_class_creates():
    recipe = _standard_recipe()
    ConfigHandler(recipe)
    assert recipe.main_runs == 1


def test_handler_from_instance_already_created():
    recipe = _standard_recipe()
    page = recipe()
    page.create()
    h = ConfigHandler(page)
    assert recipe.main_runs == 1
    assert h("server.host") == "localhost"


def test_handler_from_instance_not_created():
    recipe = _standard_recipe()
    h = ConfigHandler(recipe())
    assert recipe.main_runs == 1
    assert h("server.host") == "localhost"


def test_handler_from_config_py_path(tmp_path):
    config_py = tmp_path / "config.py"
    config_py.write_text(textwrap.dedent("""
        from genro_builders.contrib.config import ConfigBuilder

        class InstanceConfig(ConfigBuilder):
            def main(self, root):
                root.configuration().server(host="from-file")
    """))
    h = ConfigHandler(config_py)
    assert h("server.host") == "from-file"


def test_config_py_zero_subclasses_raises(tmp_path):
    config_py = tmp_path / "config.py"
    config_py.write_text("from genro_builders.contrib.config import ConfigBuilder\n")
    with pytest.raises(ValueError, match="exactly one ConfigBuilder subclass"):
        ConfigHandler(config_py)


def test_config_py_many_subclasses_raises(tmp_path):
    config_py = tmp_path / "config.py"
    config_py.write_text(textwrap.dedent("""
        from genro_builders.contrib.config import ConfigBuilder

        class One(ConfigBuilder):
            def main(self, root): root.configuration()

        class Two(ConfigBuilder):
            def main(self, root): root.configuration()
    """))
    with pytest.raises(ValueError, match=r"One.*Two"):
        ConfigHandler(config_py)


def test_config_py_imported_subclass_not_counted(tmp_path):
    (tmp_path / "base_recipe.py").write_text(textwrap.dedent("""
        from genro_builders.contrib.config import ConfigBuilder

        class BaseRecipe(ConfigBuilder):
            pass
    """))
    config_py = tmp_path / "config.py"
    config_py.write_text(textwrap.dedent(f"""
        import sys
        sys.path.insert(0, {str(tmp_path)!r})
        from base_recipe import BaseRecipe

        class InstanceConfig(BaseRecipe):
            def main(self, root):
                root.configuration().server(host="layered")
    """))
    h = ConfigHandler(config_py)
    assert h("server.host") == "layered"


def test_bad_source_type_raises():
    with pytest.raises(TypeError, match="config.py path"):
        ConfigHandler(42)


def test_bad_source_class_raises():
    with pytest.raises(TypeError, match="BuilderBase"):
        ConfigHandler(dict)


def test_recipe_building_no_root_element_raises():
    def body(root):
        pass

    with pytest.raises(ValueError, match="exactly one root element"):
        ConfigHandler(_recipe(body))
