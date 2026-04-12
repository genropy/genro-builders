# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for HtmlBuilder."""

import pytest

from genro_builders.builder_bag import BuilderBag as Bag
from genro_builders.contrib.html import HtmlBuilder


class TestHtmlBuilder:
    """Tests for HtmlBuilder."""

    def test_create_bag_with_html_builder(self):
        """Creates Bag with HtmlBuilder."""
        bag = Bag(builder=HtmlBuilder)
        assert isinstance(bag.builder, HtmlBuilder)

    def test_valid_html_tags(self):
        """HtmlBuilder knows common HTML5 tags via schema."""
        bag = Bag(builder=HtmlBuilder)
        # Check tags exist in schema using 'in' operator
        assert "div" in bag.builder
        assert "span" in bag.builder
        assert "p" in bag.builder
        assert "html" in bag.builder

    def test_void_elements(self):
        """HtmlBuilder knows void elements via schema."""
        bag = Bag(builder=HtmlBuilder)
        # Void elements exist in schema
        assert "br" in bag.builder
        assert "hr" in bag.builder
        assert "img" in bag.builder

    def test_create_div(self):
        """Creates div element, returns BagNode."""
        from genro_bag import BagNode

        bag = Bag(builder=HtmlBuilder)
        node = bag.div(id="main", class_="container")

        assert isinstance(node, BagNode)
        assert node.node_tag == "div"
        assert node.attr.get("id") == "main"
        assert node.attr.get("class_") == "container"

    def test_create_void_element(self):
        """Void elements have None value by default."""
        bag = Bag(builder=HtmlBuilder)
        node = bag.br()

        assert node.value is None
        assert node.node_tag == "br"

    def test_create_element_with_value(self):
        """Elements can have text content."""
        bag = Bag(builder=HtmlBuilder)
        node = bag.p("Hello, World!")

        assert node.value == "Hello, World!"
        assert node.node_tag == "p"

    def test_nested_elements(self):
        """Creates nested HTML structure."""
        bag = Bag(builder=HtmlBuilder)
        div = bag.div(id="main")
        div.p("Paragraph text")
        div.span("Span text")

        assert len(div.value) == 2
        assert div.value.get_node("p_0").value == "Paragraph text"
        assert div.value.get_node("span_0").value == "Span text"

    def test_invalid_tag_raises(self):
        """Invalid tag raises AttributeError."""
        bag = Bag(builder=HtmlBuilder)

        with pytest.raises(AttributeError, match="has no attribute 'notarealtag'"):
            bag.notarealtag()

    def test_builder_inheritance_in_nested(self):
        """Nested bags inherit builder."""
        bag = Bag(builder=HtmlBuilder)
        div = bag.div()
        div.p("test")

        assert div.value.builder is bag.builder

    def test_auto_label_generation(self):
        """Labels are auto-generated uniquely."""
        bag = Bag(builder=HtmlBuilder)
        bag.div()
        bag.div()
        bag.div()

        labels = list(bag.keys())
        assert labels == ["div_0", "div_1", "div_2"]


def html(setup):
    """Helper: create builder, populate source, build and return rendered output."""
    builder = HtmlBuilder()
    setup(builder.source)
    builder.build()
    return builder.render()


class TestHtmlBuilderRender:
    """Tests for HtmlBuilder rendering via HtmlRenderer."""

    def test_render_simple(self):
        """render() generates HTML string."""
        result = html(lambda s: s.p("Hello"))
        assert "<p>Hello</p>" in result

    def test_render_nested(self):
        """render() handles nested elements."""
        def populate(s):
            div = s.div(id="main")
            div.p("Content")
        result = html(populate)
        assert '<div id="main">' in result
        assert "<p>Content</p>" in result
        assert "</div>" in result

    def test_render_void_elements(self):
        """Void elements render without closing tag."""
        def populate(s):
            s.br()
            s.meta(charset="utf-8")
        result = html(populate)
        assert "<br>" in result
        assert "</br>" not in result
        assert '<meta charset="utf-8">' in result
        assert "</meta>" not in result

    def test_render_page_structure(self):
        """render() generates complete page structure."""
        def populate(s):
            head = s.head()
            head.title("Test")
            head.meta(charset="utf-8")
            body = s.body()
            body.div(id="main").p("Hello")
        result = html(populate)
        assert "<head>" in result
        assert "</head>" in result
        assert "<body>" in result
        assert "</body>" in result
        assert "<title>Test</title>" in result
        assert 'id="main"' in result
        assert "<p>Hello</p>" in result


class TestHtmlBuilderIntegration:
    """Integration tests for HTML builder with Bag."""

    def test_complex_html_structure(self):
        """Creates complex HTML structure."""
        def populate(s):
            head = s.head()
            head.meta(charset="utf-8")
            head.title("My Website")
            head.link(rel="stylesheet", href="style.css")

            body = s.body()
            header = body.header(id="header")
            header.h1("Welcome")
            nav = header.nav()
            ul = nav.ul()
            ul.li("Home")
            ul.li("About")
            ul.li("Contact")

            main = body.main(id="content")
            article = main.article()
            article.h2("Article Title")
            article.p("Article content goes here.")

            footer = body.footer()
            footer.p("Copyright 2025")

        result = html(populate)
        assert '<header id="header">' in result
        assert "<nav>" in result
        assert "<ul>" in result
        assert "<li>Home</li>" in result
        assert '<main id="content">' in result
        assert "<article>" in result
        assert "<footer>" in result
