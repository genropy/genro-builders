# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for BuilderBagNode.runtime_attrs and runtime_value properties."""

from genro_builders.contrib.html import HtmlBuilder


class TestRuntimeValue:
    """Tests for node.runtime_value property."""

    def test_static_value(self):
        """runtime_value returns the literal value when no pointers."""
        builder = HtmlBuilder()
        builder.source.body().h1("Hello")
        builder.build()

        node = builder.built.get_node("body_0.h1_0")
        assert node.runtime_value == "Hello"

    def test_pointer_resolved(self):
        """runtime_value resolves ^pointer node value."""
        builder = HtmlBuilder()
        builder.data["title"] = "Resolved"
        builder.source.body().h1("^title")
        builder.build()

        node = builder.built.get_node("body_0.h1_0")
        assert node.runtime_value == "Resolved"

    def test_pointer_updates_with_data(self):
        """runtime_value reflects current data, not cached."""
        builder = HtmlBuilder()
        builder.data["title"] = "First"
        builder.source.body().h1("^title")
        builder.build()

        node = builder.built.get_node("body_0.h1_0")
        assert node.runtime_value == "First"

        builder.data["title"] = "Second"
        assert node.runtime_value == "Second"


class TestRuntimeAttrs:
    """Tests for node.runtime_attrs property."""

    def test_static_attrs(self):
        """runtime_attrs returns literal attribute values."""
        builder = HtmlBuilder()
        builder.source.body().div(id="main", class_="container")
        builder.build()

        node = builder.built.get_node("body_0.div_0")
        attrs = node.runtime_attrs
        assert attrs["id"] == "main"

    def test_pointer_attr_resolved(self):
        """runtime_attrs resolves ^pointer in attributes."""
        builder = HtmlBuilder()
        builder.data["bg"] = "#ff0000"
        builder.source.body().div(style="^bg")
        builder.build()

        node = builder.built.get_node("body_0.div_0")
        attrs = node.runtime_attrs
        assert attrs["style"] == "#ff0000"

    def test_callable_attr_resolved(self):
        """runtime_attrs executes callable attributes."""
        builder = HtmlBuilder()
        builder.data["theme.bg"] = "#fff"
        builder.data["theme.fg"] = "#333"
        builder.source.body().div(
            style=lambda bg="^theme.bg", fg="^theme.fg": f"background:{bg};color:{fg}",
        )
        builder.build()

        node = builder.built.get_node("body_0.div_0")
        attrs = node.runtime_attrs
        assert attrs["style"] == "background:#fff;color:#333"

    def test_attrs_update_with_data(self):
        """runtime_attrs reflects current data."""
        builder = HtmlBuilder()
        builder.data["color"] = "red"
        builder.source.body().div(style="^color")
        builder.build()

        node = builder.built.get_node("body_0.div_0")
        assert node.runtime_attrs["style"] == "red"

        builder.data["color"] = "blue"
        assert node.runtime_attrs["style"] == "blue"


class TestRuntimeFallback:
    """Tests for runtime_* without builder (plain node)."""

    def test_runtime_value_without_builder(self):
        """runtime_value falls back to static value without builder."""
        from genro_bag import Bag

        bag = Bag()
        bag.set_item("x", "hello")
        # Plain BagNode has no runtime_value — this tests BuilderBagNode only
        # when parent has no builder
        from genro_builders.builder_bag import BuilderBag

        bbag = BuilderBag()
        bbag.set_item("x", "hello")
        node = bbag.get_node("x")
        assert node.runtime_value == "hello"

    def test_runtime_attrs_without_builder(self):
        """runtime_attrs falls back to raw attrs without builder."""
        from genro_builders.builder_bag import BuilderBag

        bbag = BuilderBag()
        bbag.set_item("x", "hello", color="red")
        node = bbag.get_node("x")
        attrs = node.runtime_attrs
        assert attrs["color"] == "red"
