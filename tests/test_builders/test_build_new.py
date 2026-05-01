# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for the new build algorithm (rebuild from scratch).

Plain-html step: build() mirrors the source tree into the built tree
for plain html nodes — nodes whose tag, value, and attrs are static
(no pointers, no callables, no components, no iterate).

The render output is asserted as a golden value: build() is a 1:1
mirror, so given the source the rendered HTML is deterministic.
"""

from genro_bag import Bag

from genro_builders.contrib.html import HtmlManager


class HelloDiv(HtmlManager):
    def main(self, source):
        source.body().div()


class TwoChildren(HtmlManager):
    def main(self, source):
        body = source.body()
        body.div()
        body.p("hello")


class NestedNodes(HtmlManager):
    def main(self, source):
        body = source.body()
        outer = body.div(id="outer")
        outer.span("inner")


class DeepNesting(HtmlManager):
    def main(self, source):
        body = source.body()
        section = body.div(id="section")
        article = section.div(id="article")
        article.p("deep")


class TestRenderHelloDiv:
    """Single div inside body."""

    def test_render(self):
        expected = (
            "<body>\n"
            "  <div>\n"
            "</body>"
        )
        assert HelloDiv().render() == expected


class TestRenderTwoChildren:
    """Body with two flat children."""

    def test_render(self):
        expected = (
            "<body>\n"
            "  <div>\n"
            "  <p>hello</p>\n"
            "</body>"
        )
        assert TwoChildren().render() == expected


class TestRenderNestedNodes:
    """body > div(id) > span."""

    def test_render(self):
        expected = (
            "<body>\n"
            '  <div id="outer">\n'
            "    <span>inner</span>\n"
            "  </div>\n"
            "</body>"
        )
        assert NestedNodes().render() == expected


class TestRenderDeepNesting:
    """body > div > div > p, all with ids."""

    def test_render(self):
        expected = (
            "<body>\n"
            '  <div id="section">\n'
            '    <div id="article">\n'
            "      <p>deep</p>\n"
            "    </div>\n"
            "  </div>\n"
            "</body>"
        )
        assert DeepNesting().render() == expected


class ChunkDiv(HtmlManager):
    """Source root contains a div directly, no body wrapper."""

    def main(self, source):
        source.div("hello")


class DivWithAttrs(HtmlManager):
    def main(self, source):
        source.div(id="main", _class="container")


class BodyWithChildren(HtmlManager):
    def main(self, source):
        body = source.body()
        body.div(id="d1")
        body.p("hello")


class FullTree(HtmlManager):
    def main(self, source):
        body = source.body()
        outer = body.div(id="outer", _class="wrap")
        outer.span("inner")


class TestPlainHtmlMirror:
    """build() copies plain html nodes from source into built."""

    def _children(self, bag):
        return list(bag)

    def test_chunk_single_div(self):
        """Root with a single div: built mirrors the same shape."""
        app = ChunkDiv()
        app.run()
        built = app.page.built
        children = self._children(built)
        assert len(children) == 1
        assert children[0].node_tag == "div"
        assert children[0].value == "hello"

    def test_div_attrs_are_copied(self):
        """Attributes on the source node appear on the built node."""
        app = DivWithAttrs()
        app.run()
        built = app.page.built
        children = self._children(built)
        assert len(children) == 1
        node = children[0]
        assert node.node_tag == "div"
        assert node.attr.get("id") == "main"
        assert node.attr.get("_class") == "container"

    def test_body_with_children(self):
        """Body containing two flat children: structure mirrored."""
        app = BodyWithChildren()
        app.run()
        built = app.page.built
        roots = self._children(built)
        assert len(roots) == 1
        body = roots[0]
        assert body.node_tag == "body"
        assert isinstance(body.value, Bag)
        body_children = self._children(body.value)
        assert len(body_children) == 2
        tags = [n.node_tag for n in body_children]
        assert tags == ["div", "p"]
        assert body_children[0].attr.get("id") == "d1"
        assert body_children[1].value == "hello"

    def test_full_tree_nested(self):
        """body > div(id,class) > span: nested structure with attrs."""
        app = FullTree()
        app.run()
        built = app.page.built
        body = self._children(built)[0]
        assert body.node_tag == "body"
        outer = self._children(body.value)[0]
        assert outer.node_tag == "div"
        assert outer.attr.get("id") == "outer"
        assert outer.attr.get("_class") == "wrap"
        span = self._children(outer.value)[0]
        assert span.node_tag == "span"
        assert span.value == "inner"

    def test_render_full_tree(self):
        """End-to-end: render of mirrored built produces expected HTML."""
        app = FullTree()
        result = app.render()
        assert "<body>" in result
        assert '<div id="outer" class="wrap">' in result
        assert "<span>inner</span>" in result
        assert "</body>" in result
