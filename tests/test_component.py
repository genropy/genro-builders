# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Component error contracts (area CMP).

The runnable behaviour (single component, explicit params, reuse) is
covered by the example ``with_data/07_address_block`` through the
examples runner. This module covers what an example cannot ship: the
tree-not-forest violation raises.
"""
from __future__ import annotations

import pytest

from genro_builders.builder import component
from genro_builders.contrib.html import HtmlBuilder


def test_component_forest_raises():
    class Components:
        @component
        def twin_blocks(self, root):
            root.div("one")
            root.div("two")          # second root: a forest

    class Page(HtmlBuilder, Components):
        def main(self, root):
            root.body().twin_blocks()

    page = Page()
    page.create()                    # expansion happens at render time
    with pytest.raises(ValueError, match="tree, not a forest"):
        page.render()


def test_expansion_pointers_never_register():
    """CMP.7: the pointer_map holds the component node's own pointers
    (here the ``store`` anchor); the expansion's relative pointers
    resolve at render but register nothing."""
    from genro_builders.builder import BuilderHandler

    class Components:
        @component
        def card(self, root):
            root.div("^.label")

    class Page(HtmlBuilder, Components):
        def setup(self, data):
            data.set_item("rec.label", "x")

        def main(self, root):
            root.body().card(store="^rec")

    page = Page(name="p")
    handler = BuilderHandler(application=object())   # tracking needs an app
    handler.add_builder(page)
    page.render()
    assert "p.rec" in handler.pointer_map          # the anchor, on the node
    assert "p.rec.label" not in handler.pointer_map  # the expansion: nothing


def test_iterate_must_resolve_to_a_bag():
    from genro_builders.builder import BuilderHandler

    class Components:
        @component
        def row(self, root, node_label=None):
            root.div("^.x")

    class Page(HtmlBuilder, Components):
        def setup(self, data):
            data.set_item("scalar", 42)

        def main(self, root):
            root.body().row(iterate="^scalar")

    page = Page(name="p")
    handler = BuilderHandler()
    handler.add_builder(page)
    with pytest.raises(TypeError, match="iterate must resolve to a Bag"):
        page.render()


def test_nesting_matrix_single_in_single_and_single_in_iterate():
    """D10 matrix cells not covered by the examples (10 covers
    iterate-in-iterate, 11 covers self-recursion): a single component
    inside a single one, and a single component inside an iterate."""
    from genro_builders.builder import BuilderHandler

    class Components:
        @component
        def badge(self, root, text=None):
            root.span(text, class_="badge")

        @component
        def titled(self, root, title=None):
            box = root.div(class_="box")
            box.badge(text=title)              # single in single

        @component
        def row(self, root, node_label=None):
            tr = root.tr(datapath="." + node_label)
            td = tr.td()
            td.badge(text="^.name")            # single in iterate

    class Page(HtmlBuilder, Components):
        def setup(self, data):
            data.set_item("rows.r1.name", "one")
            data.set_item("rows.r2.name", "two")

        def main(self, root):
            body = root.body()
            body.titled(title="Hello")
            body.table().tbody().row(iterate="^rows")

    page = Page(name="p")
    handler = BuilderHandler()
    handler.add_builder(page)
    out = page.render()
    assert out.count('<span class="badge">') == 3
    assert "Hello" in out and "one" in out and "two" in out


def test_component_empty_expansion_raises():
    class Components:
        @component
        def nothing(self, root):
            pass                     # zero roots: not a tree either

    class Page(HtmlBuilder, Components):
        def main(self, root):
            root.body().nothing()

    page = Page()
    page.create()
    with pytest.raises(ValueError, match="tree, not a forest"):
        page.render()
