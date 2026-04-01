# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""MarkdownBuilder and MarkdownRenderer - Markdown document builder and renderer.

Provides elements for building Markdown documents programmatically.
MarkdownBuilder defines the schema elements, MarkdownRenderer transforms to Markdown.

Example:
    Creating a Markdown document::

        from genro_builders.builders.markdown import MarkdownBuilder

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
from ...renderer import BagRendererBase, render_handler


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

    def render(self, built_bag: Bag) -> str:
        """Render built bag to Markdown string."""
        parts = list(self._walk_render(built_bag))
        return "\n\n".join(p for p in parts if p)

    # -------------------------------------------------------------------------
    # Headings
    # -------------------------------------------------------------------------

    @render_handler
    def h1(self, node: BagNode, ctx: dict[str, Any]) -> str:
        return f"# {ctx['node_value']}"

    @render_handler
    def h2(self, node: BagNode, ctx: dict[str, Any]) -> str:
        return f"## {ctx['node_value']}"

    @render_handler
    def h3(self, node: BagNode, ctx: dict[str, Any]) -> str:
        return f"### {ctx['node_value']}"

    @render_handler
    def h4(self, node: BagNode, ctx: dict[str, Any]) -> str:
        return f"#### {ctx['node_value']}"

    @render_handler
    def h5(self, node: BagNode, ctx: dict[str, Any]) -> str:
        return f"##### {ctx['node_value']}"

    @render_handler
    def h6(self, node: BagNode, ctx: dict[str, Any]) -> str:
        return f"###### {ctx['node_value']}"

    # -------------------------------------------------------------------------
    # Block elements
    # -------------------------------------------------------------------------

    @render_handler
    def code(self, node: BagNode, ctx: dict[str, Any]) -> str:
        lang = ctx.get("lang", "")
        return f"```{lang}\n{ctx['node_value']}\n```"

    @render_handler
    def blockquote(self, node: BagNode, ctx: dict[str, Any]) -> str:
        value = ctx["node_value"]
        return "\n".join(f"> {line}" for line in value.split("\n"))

    @render_handler
    def hr(self, node: BagNode, ctx: dict[str, Any]) -> str:
        return "---"

    # -------------------------------------------------------------------------
    # Table
    # -------------------------------------------------------------------------

    @render_handler
    def table(self, node: BagNode, ctx: dict[str, Any]) -> str:
        lines: list[str] = []
        rows = node.value if isinstance(node.value, Bag) else []
        is_first = True

        for row_node in rows:
            if row_node.node_tag != "tr":
                continue
            cells = row_node.value if isinstance(row_node.value, Bag) else []
            cell_texts = [str(cell.get_value(static=True) or "") for cell in cells]

            lines.append("| " + " | ".join(cell_texts) + " |")

            if is_first:
                lines.append("| " + " | ".join("---" for _ in cell_texts) + " |")
                is_first = False

        return "\n".join(lines)

    # -------------------------------------------------------------------------
    # Lists
    # -------------------------------------------------------------------------

    @render_handler
    def ul(self, node: BagNode, ctx: dict[str, Any]) -> str:
        return self._render_list(node, "-")

    @render_handler
    def ol(self, node: BagNode, ctx: dict[str, Any]) -> str:
        return self._render_list(node, "ol")

    def _render_list(self, node: BagNode, prefix: str) -> str:
        lines: list[str] = []
        items = node.value if isinstance(node.value, Bag) else []

        for i, item_node in enumerate(items, start=1):
            text = str(item_node.get_value(static=True) or "")
            node_idx = item_node.attr.get("idx")
            if node_idx is not None:
                item_prefix = str(node_idx)
            else:
                item_prefix = f"{i}." if prefix == "ol" else prefix
            lines.append(f"{item_prefix} {text}")

        return "\n".join(lines)

    # -------------------------------------------------------------------------
    # Inline elements
    # -------------------------------------------------------------------------

    @render_handler
    def link(self, node: BagNode, ctx: dict[str, Any]) -> str:
        return f"[{ctx['node_value']}]({ctx['href']})"

    @render_handler
    def img(self, node: BagNode, ctx: dict[str, Any]) -> str:
        return f"![{ctx.get('alt', '')}]({ctx['src']})"

    @render_handler
    def bold(self, node: BagNode, ctx: dict[str, Any]) -> str:
        return f"**{ctx['node_value']}**"

    @render_handler
    def italic(self, node: BagNode, ctx: dict[str, Any]) -> str:
        return f"*{ctx['node_value']}*"

    @render_handler
    def inlinecode(self, node: BagNode, ctx: dict[str, Any]) -> str:
        return f"`{ctx['node_value']}`"


# Register renderer on builder
MarkdownBuilder._renderers = {"markdown": MarkdownRenderer}
