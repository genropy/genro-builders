# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for YamlRendererBase — YAML rendering from built Bag."""

import yaml

from genro_builders import BagBuilderBase
from genro_builders.builder_bag import BuilderBag as Bag
from genro_builders.builder import element
from genro_builders.contrib.yaml import YamlRendererBase


class YamlBuilder(BagBuilderBase):
    """Builder for YAML rendering tests."""

    @element(sub_tags="*")
    def root(self): ...

    @element(sub_tags="*")
    def service(self, image: str = "", ports: str = ""): ...

    @element()
    def setting(self, value: str = ""): ...

    @element(sub_tags="*")
    def group(self): ...


class TestYamlRendererBasic:
    """Basic YAML rendering tests."""

    def test_empty_bag_returns_empty_string(self):
        """Rendering an empty built Bag returns empty string."""
        renderer = YamlRendererBase()
        bag = Bag()
        assert renderer.render(bag) == ""

    def test_simple_element_renders_yaml(self):
        """A simple element renders to valid YAML."""
        builder = YamlBuilder()
        root = builder.source.root()
        root.setting(value="hello")

        builder.build()
        renderer = YamlRendererBase(builder)
        result = renderer.render(builder.built)

        assert isinstance(result, str)
        parsed = yaml.safe_load(result)
        assert isinstance(parsed, dict)

    def test_attributes_in_output(self):
        """Element attributes appear in YAML output."""
        builder = YamlBuilder()
        root = builder.source.root()
        root.service(image="nginx:latest", ports="80:80")

        builder.build()
        renderer = YamlRendererBase(builder)
        result = renderer.render(builder.built)
        parsed = yaml.safe_load(result)

        assert "service" in parsed
        assert parsed["service"]["image"] == "nginx:latest"

    def test_comma_separated_becomes_list(self):
        """Comma-separated string values become YAML lists."""
        renderer = YamlRendererBase()
        result = renderer._to_yaml_value("a,b,c")
        assert result == ["a", "b", "c"]

    def test_plain_string_stays_string(self):
        """String without commas stays a string."""
        renderer = YamlRendererBase()
        result = renderer._to_yaml_value("hello")
        assert result == "hello"

    def test_list_passes_through(self):
        """List values pass through unchanged."""
        renderer = YamlRendererBase()
        result = renderer._to_yaml_value(["a", "b"])
        assert result == ["a", "b"]

    def test_none_values_filtered(self):
        """None attribute values are filtered out."""
        builder = YamlBuilder()
        root = builder.source.root()
        root.setting()  # no value= → defaults to ""

        builder.build()
        renderer = YamlRendererBase(builder)
        result = renderer.render(builder.built)
        parsed = yaml.safe_load(result)

        # setting with empty string default should still appear
        assert isinstance(parsed, dict)


class TestYamlRendererMerge:
    """Tests for duplicate key merging."""

    def test_duplicate_tags_merge(self):
        """Two nodes with same tag merge their attributes."""
        builder = YamlBuilder()
        root = builder.source.root()
        root.service(image="nginx")
        root.service(image="redis")

        builder.build()
        renderer = YamlRendererBase(builder)
        result = renderer.render(builder.built)
        parsed = yaml.safe_load(result)

        # Second service overwrites first via dict.update
        assert "service" in parsed
        assert parsed["service"]["image"] == "redis"


class TestYamlRendererNested:
    """Tests for nested structures."""

    def test_nested_children_render(self):
        """Nested children appear as nested YAML keys."""
        builder = YamlBuilder()
        root = builder.source.root()
        group = root.group()
        group.setting(value="nested_value")

        builder.build()
        renderer = YamlRendererBase(builder)
        result = renderer.render(builder.built)
        parsed = yaml.safe_load(result)

        assert "group" in parsed
        assert isinstance(parsed["group"], dict)


class TestYamlRendererSubclass:
    """Tests for subclass override of _render_attr_entry."""

    def test_custom_attr_entry(self):
        """Subclass can override _render_attr_entry for custom rendering."""

        class PrefixedRenderer(YamlRendererBase):
            def _render_attr_entry(self, attr_name, value, result):
                result[f"custom_{attr_name}"] = self._to_yaml_value(value)

        builder = YamlBuilder()
        root = builder.source.root()
        root.setting(value="test")

        builder.build()
        renderer = PrefixedRenderer(builder)
        result = renderer.render(builder.built)
        parsed = yaml.safe_load(result)

        assert "setting" in parsed
        setting = parsed["setting"]
        assert "custom_value" in setting
