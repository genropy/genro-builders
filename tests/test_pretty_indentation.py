# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""``pretty=True``: one node per line, two spaces per level of depth.

Depth is read off the node's fullpath, which works by itself for the
document tree. A component expansion is built in a throw-away root of its
own (``_expansion_root``), so its nodes are rooted at 0 while they are
emitted INSIDE the document: without help they would come out flush left.
``depth_offset`` carries the component node's depth across that boundary
and accumulates through nested and recursive expansions.

Indentation is cosmetic — the markup is valid either way — so these tests
assert the leading whitespace, which is the only thing that was wrong.
"""
from __future__ import annotations

from genro_builders.builder import BuilderHandler, component
from genro_builders.contrib.html import HtmlBuilder


def _render(page_cls):
    page = page_cls()
    BuilderHandler().add_builder(page)
    return page.render(target=False, pretty=True)


def test_plain_tree_indents_by_depth():
    class Page(HtmlBuilder):
        def main(self, root) -> None:
            root.body().ul().li("alpha")

    assert _render(Page) == (
        "<body>\n"
        "  <ul>\n"
        "    <li>alpha</li>\n"
        "  </ul>\n"
        "</body>\n"
    )


def test_expansion_indents_as_a_child_of_the_component_node():
    """The rows of an iterate sit where the component sits, not at 0."""
    class Components:
        @component
        def row(self, root, node_label=None):
            root.li(f"^.{node_label}.name")

    class Page(HtmlBuilder, Components):
        def setup(self, data):
            data.set_item("items.a.name", "alpha")
            data.set_item("items.b.name", "beta")

        def main(self, root) -> None:
            root.body().ul().row(iterate="^items")

    assert _render(Page) == (
        "<body>\n"
        "  <ul>\n"
        "    <li>alpha</li>\n"
        "    <li>beta</li>\n"
        "  </ul>\n"
        "</body>\n"
    )


def test_offset_accumulates_through_a_recursive_component():
    """Each expansion level adds its own depth to the one it came from."""
    class Tree:
        @component
        def branch(self, root, node_label=None):
            li = root.li(datapath=f".{node_label}")
            li.span("^.name")
            li.ul().branch(iterate="^.children")

    class Page(HtmlBuilder, Tree):
        def setup(self, data):
            data.set_item("tree.n1.name", "root")
            data.set_item("tree.n1.children.n2.name", "child")

        def main(self, root) -> None:
            root.body().ul().branch(iterate="^tree")

    out = _render(Page)
    assert "    <li>\n" in out                    # depth 2: inside body.ul
    assert "      <span>root</span>\n" in out     # depth 3: inside that li
    assert "        <li>\n" in out                # depth 4: the nested row
    assert "          <span>child</span>\n" in out  # depth 5


def test_pretty_off_emits_no_whitespace():
    class Components:
        @component
        def row(self, root, node_label=None):
            root.li(f"^.{node_label}.name")

    class Page(HtmlBuilder, Components):
        def setup(self, data):
            data.set_item("items.a.name", "alpha")

        def main(self, root) -> None:
            root.body().ul().row(iterate="^items")

    page = Page()
    BuilderHandler().add_builder(page)
    assert page.render(target=False) == "<body><ul><li>alpha</li></ul></body>"
