# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for abs_datapath: absolute, relative, and symbolic path resolution."""
from __future__ import annotations

import pytest

from genro_builders.builder import BagBuilderBase, element


class PathBuilder(BagBuilderBase):
    """Builder for abs_datapath tests."""

    @element(sub_tags="*")
    def container(self): ...

    @element(sub_tags="")
    def item(self): ...


class TestAbsDatapath:
    """Tests for BuilderBagNode.abs_datapath()."""

    def test_absolute_path_unchanged(self):
        """Absolute path is returned as-is."""
        builder = PathBuilder()
        node = builder.source.item("hello")
        assert node.abs_datapath("user.name") == "user.name"

    def test_relative_path_from_root_raises(self):
        """Relative path at root level raises ValueError (no datapath context)."""
        builder = PathBuilder()
        node = builder.source.item("hello")
        with pytest.raises(ValueError, match="without a datapath context"):
            node.abs_datapath(".name")

    def test_relative_path_with_datapath(self):
        """Relative path resolves from ancestor's datapath."""
        builder = PathBuilder()
        c = builder.source.container(datapath="customer")
        node = c.item("hello")
        assert node.abs_datapath(".name") == "customer.name"

    def test_relative_path_nested_datapath(self):
        """Nested datapaths compose correctly."""
        builder = PathBuilder()
        outer = builder.source.container(datapath="app")
        inner = outer.container(datapath=".user")
        node = inner.item("hello")
        assert node.abs_datapath(".email") == "app.user.email"

    def test_symbolic_path_with_node_id(self):
        """#node_id resolves to that node's datapath."""
        builder = PathBuilder()
        builder.source.container(node_id="addr", datapath="customer.address")
        node = builder.source.item("test")
        assert node.abs_datapath("#addr.street") == "customer.address.street"

    def test_symbolic_path_node_id_only(self):
        """#node_id without suffix returns the node's datapath."""
        builder = PathBuilder()
        builder.source.container(node_id="addr", datapath="customer.address")
        node = builder.source.item("test")
        assert node.abs_datapath("#addr") == "customer.address"

    def test_symbolic_path_missing_node_id_raises(self):
        """#node_id with unknown id raises KeyError."""
        builder = PathBuilder()
        node = builder.source.item("test")
        with pytest.raises(KeyError):
            node.abs_datapath("#nonexistent.foo")

    def test_symbolic_path_node_without_datapath(self):
        """#node_id on a node without explicit datapath resolves via ancestors."""
        builder = PathBuilder()
        outer = builder.source.container(datapath="root")
        outer.container(node_id="inner")
        node = builder.source.item("test")
        # inner has no explicit datapath, but is inside "root"
        result = node.abs_datapath("#inner.field")
        assert result.endswith(".field")
