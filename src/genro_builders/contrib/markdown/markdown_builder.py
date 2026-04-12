# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""MarkdownBuilder and MarkdownRenderer - Markdown document builder and renderer.

Provides elements for building Markdown documents programmatically.
MarkdownBuilder defines the schema elements, MarkdownRenderer transforms to Markdown.

Example:
    Creating a Markdown document::

        from genro_builders.contrib.markdown import MarkdownBuilder

        builder = MarkdownBuilder()
        builder.source.h1("My Document")
        builder.source.p("This is a paragraph.")

        table = builder.source.table()
        header = table.tr()
        header.th("Name")
        header.th("Value")
        row = table.tr()
        row.td("foo")
        row.td("bar")

        builder.source.code("print('hello')", lang="python")

        output = builder.build()
"""

from __future__ import annotations

from typing import Any

from genro_bag import Bag, BagNode

from ...builder import BagBuilderBase, element
from ...renderer import BagRendererBase, renderer


class MarkdownBuilder(BagBuilderBase):
    """Builder for Markdown documents."""

    # -------------------------------------------------------------------------
    # Headings
    # -------------------------------------------------------------------------

    @element(sub_tags="")
    def h1(self, node_value: str):
        """Level 1 heading."""
        ...

    @element(sub_tags="")
    def h2(self, node_value: str):
        """Level 2 heading."""
        ...

    @element(sub_tags="")
    def h3(self, node_value: str):
        """Level 3 heading."""
        ...

    @element(sub_tags="")
    def h4(self, node_value: str):
        """Level 4 heading."""
        ...

    @element(sub_tags="")
    def h5(self, node_value: str):
        """Level 5 heading."""
        ...

    @element(sub_tags="")
    def h6(self, node_value: str):
        """Level 6 heading."""
        ...

    # -------------------------------------------------------------------------
    # Block elements
    # -------------------------------------------------------------------------

    @element(sub_tags="")
    def p(self, node_value: str):
        """Paragraph."""
        ...

    @element(sub_tags="")
    def code(self, node_value: str, lang: str = ""):
        """Code block with optional language."""
        ...

    @element(sub_tags="")
    def blockquote(self, node_value: str):
        """Blockquote."""
        ...

    @element(sub_tags="")
    def hr(self):
        """Horizontal rule."""
        ...

    # -------------------------------------------------------------------------
    # Table elements
    # -------------------------------------------------------------------------

    @element(sub_tags="tr")
    def table(self):
        """Table container."""
        ...

    @element(sub_tags="th,td")
    def tr(self):
        """Table row."""
        ...

    @element(sub_tags="")
    def th(self, node_value: str):
        """Table header cell."""
        ...

    @element(sub_tags="")
    def td(self, node_value: str):
        """Table data cell."""
        ...

    # -------------------------------------------------------------------------
    # List elements
    # -------------------------------------------------------------------------

    @element(sub_tags="li")
    def ul(self):
        """Unordered list."""
        ...

    @element(sub_tags="li")
    def ol(self):
        """Ordered list."""
        ...

    @element(sub_tags="")
    def li(self, node_value: str, idx: str | int | None = None):
        """List item."""
        ...

    # -------------------------------------------------------------------------
    # Inline elements
    # -------------------------------------------------------------------------

    @element(sub_tags="")
    def link(self, node_value: str, href: str):
        """Hyperlink."""
        ...

    @element(sub_tags="")
    def img(self, src: str, alt: str = ""):
        """Image."""
        ...

    @element(sub_tags="")
    def bold(self, node_value: str):
        """Bold text."""
        ...

    @element(sub_tags="")
    def italic(self, node_value: str):
        """Italic text."""
        ...

    @element(sub_tags="")
    def inlinecode(self, node_value: str):
        """Inline code."""
        ...

    @element(sub_tags="")
    def text(self, node_value: str):
        """Plain text."""
        ...


# =============================================================================
# MarkdownRenderer
# =============================================================================


class MarkdownRenderer(BagRendererBase):
    """Renderer for Markdown documents."""

    def render(self, built_bag: Bag, output: Any = None) -> str:
        """Render built bag to Markdown string."""
        root = self._walk_render(built_bag)
        return "\n\n".join(p for p in root if p)

    # -------------------------------------------------------------------------
    # Headings — declarative via template
    # -------------------------------------------------------------------------

    @renderer(template="# {node_value}")
    def h1(self): ...

    @renderer(template="## {node_value}")
    def h2(self): ...

    @renderer(template="### {node_value}")
    def h3(self): ...

    @renderer(template="#### {node_value}")
    def h4(self): ...

    @renderer(template="##### {node_value}")
    def h5(self): ...

    @renderer(template="###### {node_value}")
    def h6(self): ...

    # -------------------------------------------------------------------------
    # Block elements
    # -------------------------------------------------------------------------

    @renderer(template="```{lang}\n{node_value}\n```")
    def code(self): ...

    @renderer()
    def blockquote(self, node: BagNode, parent: list) -> str:
        value = str(node.runtime_value or "")
        return "\n".join(f"> {line}" for line in value.split("\n"))

    @renderer(template="---")
    def hr(self): ...

    # -------------------------------------------------------------------------
    # Table
    # -------------------------------------------------------------------------

    @renderer()
    def table(self, node: BagNode, parent: list) -> str:
        lines: list[str] = []
        rows = node.value if isinstance(node.value, Bag) else []
        is_first = True

        for row_node in rows:
            if row_node.node_tag != "tr":
                continue
            cells = row_node.value if isinstance(row_node.value, Bag) else []
            cell_texts = [
                str(cell.evaluate_on_node(self.builder.data)["node_value"] or "")
                for cell in cells
            ]

            lines.append("| " + " | ".join(cell_texts) + " |")

            if is_first:
                lines.append("| " + " | ".join("---" for _ in cell_texts) + " |")
                is_first = False

        return "\n".join(lines)

    # -------------------------------------------------------------------------
    # Lists
    # -------------------------------------------------------------------------

    @renderer()
    def ul(self, node: BagNode, parent: list) -> str:
        return self._render_list(node, "-")

    @renderer()
    def ol(self, node: BagNode, parent: list) -> str:
        return self._render_list(node, "ol")

    def _render_list(self, node: BagNode, prefix: str) -> str:
        lines: list[str] = []
        items = node.value if isinstance(node.value, Bag) else []

        for i, item_node in enumerate(items, start=1):
            resolved = item_node.evaluate_on_node(self.builder.data)
            text = str(resolved["node_value"] or "")
            node_idx = resolved["attrs"].get("idx")
            if node_idx is not None:
                item_prefix = str(node_idx)
            else:
                item_prefix = f"{i}." if prefix == "ol" else prefix
            lines.append(f"{item_prefix} {text}")

        return "\n".join(lines)

    # -------------------------------------------------------------------------
    # Inline elements
    # -------------------------------------------------------------------------

    @renderer(template="[{node_value}]({href})")
    def link(self): ...

    @renderer(template="![{alt}]({src})")
    def img(self): ...

    @renderer(template="**{node_value}**")
    def bold(self): ...

    @renderer(template="*{node_value}*")
    def italic(self): ...

    @renderer(template="`{node_value}`")
    def inlinecode(self): ...


# Register renderer on builder
MarkdownBuilder._renderers = {"markdown": MarkdownRenderer}
