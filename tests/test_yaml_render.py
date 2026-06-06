# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""End-to-end tests for the core ``yaml`` render mode (YamlRenderer).

YAML is a shared render mode on ``BagBuilderBase`` (like ``xml``): any
builder serves it via ``renderer_yaml``. These tests drive a real
handler on an ad-hoc grammar and assert on the parsed YAML — outcomes,
never internals. PyYAML is an optional dependency; the suite skips if it
is absent.
"""
from __future__ import annotations

import pytest

from genro_builders import BagBuilderBase
from genro_builders.builder import element
from genro_builders.builder_handler import BuilderHandler

yaml = pytest.importorskip("yaml")


class CfgBuilder(BagBuilderBase):
    """Ad-hoc grammar exercising the YAML renderer."""

    _name = "cfg_yaml_test"

    @element(sub_tags="*")
    def root(self): ...

    @element(sub_tags="*")
    def service(self, image: str = "", ports: str = ""): ...

    @element()
    def setting(self, value: str = ""): ...


class CfgHandler(BuilderHandler):
    builder_class = CfgBuilder

    def __init__(self, build, **kwargs):
        self._build = build
        super().__init__(**kwargs)

    def main(self, root):
        self._build(root)


def _render(build) -> dict:
    handler = CfgHandler(build)
    handler.create()
    return yaml.safe_load(handler.render(mode="yaml", target=False))


def test_simple_element_renders_attributes():
    def build(root):
        root.service(image="nginx")

    assert _render(build) == {"service": {"image": "nginx"}}


def test_comma_string_becomes_list():
    def build(root):
        root.service(image="nginx", ports="80,443")

    assert _render(build)["service"]["ports"] == ["80", "443"]


def test_children_nest_under_parent():
    def build(root):
        root.service(image="nginx").setting(value="x")

    assert _render(build) == {
        "service": {"image": "nginx", "setting": {"value": "x"}}
    }


def test_ambiguous_string_is_quoted_not_coerced():
    """``on`` must round-trip as the string 'on', not the bool True."""
    def build(root):
        root.setting(value="on")

    assert _render(build) == {"setting": {"value": "on"}}


def test_none_attributes_are_dropped():
    def build(root):
        root.service(image="nginx", ports=None)

    assert _render(build) == {"service": {"image": "nginx"}}
