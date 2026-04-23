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
