# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for MarkdownBuilder with MarkdownRenderer.

Tests cover:
- Heading elements (h1-h6)
- Paragraph and text blocks
- Code blocks with language
- Tables with headers and rows
- Lists (ordered and unordered)
- Inline elements (bold, italic, link)
- build() output
"""

from genro_builders.contrib.markdown import MarkdownBuilder


def md(setup):
    """Helper: create builder, populate source, build and return rendered output."""
    builder = MarkdownBuilder()
    setup(builder.source)
    builder.build()
    return builder.render()


class TestMarkdownHeadings:
    """Tests for Markdown heading elements."""

    def test_h1(self):
        """h1 generates # prefix."""
        result = md(lambda s: s.h1("Title"))
        assert result == "# Title"

    def test_h2(self):
        """h2 generates ## prefix."""
        result = md(lambda s: s.h2("Subtitle"))
        assert result == "## Subtitle"

    def test_h3(self):
        """h3 generates ### prefix."""
        result = md(lambda s: s.h3("Section"))
        assert result == "### Section"

    def test_multiple_headings(self):
        """Multiple headings separated by blank lines."""
        def populate(s):
            s.h1("Title")
            s.h2("Subtitle")
        result = md(populate)
        assert "# Title" in result
        assert "## Subtitle" in result
        assert "\n\n" in result


class TestMarkdownParagraph:
    """Tests for Markdown paragraph element."""

    def test_paragraph(self):
        """p generates plain text."""
        result = md(lambda s: s.p("This is a paragraph."))
        assert result == "This is a paragraph."

    def test_multiple_paragraphs(self):
        """Multiple paragraphs separated by blank lines."""
        def populate(s):
            s.p("First paragraph.")
            s.p("Second paragraph.")
        result = md(populate)
        assert "First paragraph." in result
        assert "Second paragraph." in result
        assert "\n\n" in result


class TestMarkdownCode:
    """Tests for Markdown code block element."""

    def test_code_block(self):
        """code generates fenced code block."""
        result = md(lambda s: s.code("print('hello')"))
        assert "```" in result
        assert "print('hello')" in result

    def test_code_block_with_language(self):
        """code with lang attribute adds language."""
        result = md(lambda s: s.code("def foo(): pass", lang="python"))
        assert "```python" in result
        assert "def foo(): pass" in result


class TestMarkdownBlockquote:
    """Tests for Markdown blockquote element."""

    def test_blockquote(self):
        """blockquote generates > prefix."""
        result = md(lambda s: s.blockquote("A quote."))
        assert result == "> A quote."

    def test_blockquote_multiline(self):
        """blockquote handles multiple lines."""
        result = md(lambda s: s.blockquote("Line 1\nLine 2"))
        assert "> Line 1" in result
        assert "> Line 2" in result


class TestMarkdownHorizontalRule:
    """Tests for Markdown horizontal rule element."""

    def test_hr(self):
        """hr generates ---."""
        result = md(lambda s: s.hr())
        assert result == "---"


class TestMarkdownTable:
    """Tests for Markdown table elements."""

    def test_simple_table(self):
        """Table with header and rows."""
        def populate(s):
            table = s.table()
            header = table.tr()
            header.th("Name")
            header.th("Value")
            row = table.tr()
            row.td("foo")
            row.td("bar")
        result = md(populate)
        assert "| Name | Value |" in result
        assert "| --- | --- |" in result
        assert "| foo | bar |" in result

    def test_table_multiple_rows(self):
        """Table with multiple data rows."""
        def populate(s):
            table = s.table()
            header = table.tr()
            header.th("A")
            header.th("B")
            for i in range(3):
                row = table.tr()
                row.td(f"a{i}")
                row.td(f"b{i}")
        result = md(populate)
        assert "| a0 | b0 |" in result
        assert "| a1 | b1 |" in result
        assert "| a2 | b2 |" in result


class TestMarkdownLists:
    """Tests for Markdown list elements."""

    def test_unordered_list(self):
        """ul generates - prefix."""
        def populate(s):
            ul = s.ul()
            ul.li("Item 1")
            ul.li("Item 2")
            ul.li("Item 3")
        result = md(populate)
        assert "- Item 1" in result
        assert "- Item 2" in result
        assert "- Item 3" in result

    def test_ordered_list(self):
        """ol generates numbered prefix."""
        def populate(s):
            ol = s.ol()
            ol.li("First")
            ol.li("Second")
            ol.li("Third")
        result = md(populate)
        assert "1. First" in result
        assert "2. Second" in result
        assert "3. Third" in result


class TestMarkdownInline:
    """Tests for Markdown inline elements."""

    def test_link(self):
        """link generates [text](href)."""
        result = md(lambda s: s.link("Click here", href="https://example.com"))
        assert "[Click here](https://example.com)" in result

    def test_img(self):
        """img generates ![alt](src)."""
        result = md(lambda s: s.img(src="image.png", alt="My Image"))
        assert "![My Image](image.png)" in result

    def test_bold(self):
        """bold generates **text**."""
        result = md(lambda s: s.bold("important"))
        assert "**important**" in result

    def test_italic(self):
        """italic generates *text*."""
        result = md(lambda s: s.italic("emphasis"))
        assert "*emphasis*" in result


class TestMarkdownBuild:
    """Tests for MarkdownBuilder.build()."""

    def test_build_returns_string(self):
        """build() returns markdown string."""
        def populate(s):
            s.h1("Test")
            s.p("Content")
        result = md(populate)
        assert isinstance(result, str)
        assert "# Test" in result
        assert "Content" in result


class TestMarkdownCompleteDocument:
    """Tests for complete Markdown documents."""

    def test_full_document(self):
        """Build a complete document with multiple elements."""
        def populate(s):
            s.h1("My Document")
            s.p("Introduction paragraph.")
            s.h2("Code Example")
            s.code("x = 1 + 2", lang="python")
            s.h2("Data Table")
            table = s.table()
            header = table.tr()
            header.th("Column A")
            header.th("Column B")
            row = table.tr()
            row.td("value1")
            row.td("value2")
            s.h2("Steps")
            ol = s.ol()
            ol.li("First step")
            ol.li("Second step")

        result = md(populate)

        assert "# My Document" in result
        assert "## Code Example" in result
        assert "```python" in result
        assert "| Column A | Column B |" in result
        assert "1. First step" in result
