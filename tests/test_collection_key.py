# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for ``collection_key``: an element declared a collection labels
each child by its natural key instead of an auto-label.

The key is either a child attribute name (``code`` -> label =
``attr['code']``) or a ``${...}`` template over child attributes. Strict
in both forms: a missing attribute, a duplicate resulting key among
siblings, or an explicit ``node_label=`` on a child all raise.

Exercised through a minimal inline builder, no dialect dependency.
"""
from __future__ import annotations

import pytest

from genro_builders.builder import BuilderBase, BuilderHandler, element


class _CfgBuilder(BuilderBase):
    _name = "_cfgtest"
    _default_render_mode = "xml"

    @element(sub_tags="database", collection_key="code")
    def databases(self, **kwargs): ...

    @element(parent_tags="databases")
    def database(self, **kwargs): ...

    @element(sub_tags="shard", collection_key="${code}_${impl}")
    def shards(self, **kwargs): ...

    @element(parent_tags="shards")
    def shard(self, **kwargs): ...

    @element(sub_tags="item")
    def plainlist(self, **kwargs): ...

    @element(parent_tags="plainlist")
    def item(self, **kwargs): ...


def _build(main):
    class _H(_CfgBuilder):
        pass

    _H.main = lambda self, root: main(root)
    page = _H()
    BuilderHandler().add_builder(page)
    return page


def _children(page):
    """The labels of the (single) container's children."""
    container = next(iter(page.source))
    return [n.label for n in container.value]


def test_attribute_key_labels_children_by_value():
    """``collection_key='code'`` makes each child's label its ``code``."""
    db = _build(
        lambda root: (
            lambda d: (d.database(code="maindb"), d.database(code="logistic"))
        )(root.databases()),
    )
    assert _children(db) == ["maindb", "logistic"]


def test_attribute_key_child_reachable_by_natural_key():
    """The child is reachable by its key, carrying its other attributes."""
    page = _build(lambda root: root.databases().database(code="maindb", name="abh"))
    container = next(iter(page.source))
    assert container.value.get_node("maindb").attr.get("name") == "abh"


def test_template_key_composes_label():
    """A ``${...}`` template composes the label from several attributes."""
    page = _build(lambda root: root.shards().shard(code="a", impl="pg"))
    assert _children(page) == ["a_pg"]


def test_missing_key_attribute_raises():
    """A collection member without its key attribute is an error."""
    with pytest.raises(ValueError):
        _build(lambda root: root.databases().database(name="no-code"))


def test_missing_template_part_raises():
    """A template part with no matching attribute is an error."""
    with pytest.raises(ValueError):
        _build(lambda root: root.shards().shard(code="a"))


def test_duplicate_key_raises():
    """Two children resolving to the same key clash."""
    def dup(root):
        d = root.databases()
        d.database(code="same")
        d.database(code="same")

    with pytest.raises(ValueError):
        _build(dup)


def test_explicit_node_label_on_collection_child_raises():
    """An explicit ``node_label=`` conflicts with the collection identity."""
    with pytest.raises(ValueError):
        _build(lambda root: root.databases().database(code="x", node_label="forced"))


def test_non_collection_still_auto_labels():
    """A container WITHOUT collection_key keeps auto-labelling its children."""
    page = _build(
        lambda root: (
            lambda p: (p.item(), p.item())
        )(root.plainlist()),
    )
    assert _children(page) == ["item_0", "item_1"]
