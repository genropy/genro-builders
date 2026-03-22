# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Builder utilities - helper functions for BagBuilderBase.

Separate module to keep builder.py focused on core functionality.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .builder import BagBuilderBase


def quick_ref(builder: BagBuilderBase, title: str | None = None) -> str:
    """Generate quick reference for the builder schema.

    Creates a compact text reference divided into 3 sections:
    - Abstract: base elements for inheritance
    - Elements: pure declarative elements
    - Components: elements with body logic

    For each entry shows: name, parameters, and first line of docstring.

    Args:
        builder: The builder instance.
        title: Optional title. Defaults to class name.

    Returns:
        Formatted text string.
    """
    builder_name = title or type(builder).__name__
    lines: list[str] = [f"=== {builder_name} Quick Reference ===", ""]

    # Collect by type
    abstracts: list[tuple[str, dict]] = []
    elements: list[tuple[str, dict]] = []
    components: list[tuple[str, dict]] = []

    for node in builder.schema:
        name = node.label
        info = builder.get_schema_info(name)

        if name.startswith("@"):
            abstracts.append((name[1:], info))
        elif info.get("is_component"):
            components.append((name, info))
        else:
            elements.append((name, info))

    def format_entry(name: str, info: dict, prefix: str = "") -> str:
        """Format a single entry."""
        sub_tags = info.get("sub_tags")
        parent_tags = info.get("parent_tags")
        inherits = info.get("inherits_from")

        params = []
        if sub_tags is not None:
            if sub_tags == "":
                params.append('sub_tags=""')
            elif sub_tags == "*":
                params.append('sub_tags="*"')
            else:
                params.append(f'sub_tags="{sub_tags}"')
        if parent_tags:
            params.append(f'parent_tags="{parent_tags}"')
        if inherits:
            params.append(f'inherits_from="{inherits}"')

        param_str = f"({', '.join(params)})" if params else ""

        # Docstring first line
        doc = info.get("documentation") or ""
        docline = doc.split("\n")[0].strip() if doc else ""

        return f"  {prefix}{name}{param_str}  {docline}"

    # Abstract section
    if abstracts:
        lines.append("ABSTRACT")
        lines.append("-" * 40)
        for name, info in sorted(abstracts):
            lines.append(format_entry(name, info, prefix="@"))
        lines.append("")

    # Elements section
    if elements:
        lines.append("ELEMENTS")
        lines.append("-" * 40)
        for name, info in sorted(elements):
            lines.append(format_entry(name, info))
        lines.append("")

    # Components section
    if components:
        lines.append("COMPONENTS")
        lines.append("-" * 40)
        for name, info in sorted(components):
            lines.append(format_entry(name, info))
        lines.append("")

    return "\n".join(lines)


def print_ref(
    builder: BagBuilderBase,
    destination: str | Path | None = None,
    title: str | None = None,
) -> bytes | None:
    """Generate PDF reference for the builder schema using genro-print.

    Creates a formatted PDF document with the builder's schema reference,
    divided into Abstract, Elements, and Components sections.

    Requires genro-print to be installed.

    Args:
        builder: The builder instance.
        destination: Optional file path to save the PDF. If None, returns bytes.
        title: Optional title. Defaults to class name.

    Returns:
        PDF bytes if destination is None, otherwise None (file is written).

    Raises:
        ImportError: If genro-print is not installed.
    """
    try:
        from genro_print.builders import ReportLabBuilder
    except ImportError as e:
        msg = "genro-print required: pip install genro-print"
        raise ImportError(msg) from e

    from .bag import Bag

    builder_name = title or type(builder).__name__

    # Collect by type
    abstracts: list[tuple[str, dict[str, Any]]] = []
    elements: list[tuple[str, dict[str, Any]]] = []
    components: list[tuple[str, dict[str, Any]]] = []

    for node in builder.schema:
        name = node.label
        info = builder.get_schema_info(name)

        if name.startswith("@"):
            abstracts.append((name[1:], info))
        elif info.get("is_component"):
            components.append((name, info))
        else:
            elements.append((name, info))

    # Build PDF document
    doc = Bag(builder=ReportLabBuilder)
    doc.document(title=f"{builder_name} Reference")

    # Title
    doc.paragraph(f"<b>{builder_name} Quick Reference</b>", style="Title")
    doc.spacer(height=5.0)

    def format_params(info: dict[str, Any]) -> str:
        """Format parameters string."""
        sub_tags = info.get("sub_tags")
        parent_tags = info.get("parent_tags")
        inherits = info.get("inherits_from")

        params = []
        if sub_tags is not None:
            if sub_tags == "":
                params.append('sub_tags=""')
            elif sub_tags == "*":
                params.append('sub_tags="*"')
            else:
                params.append(f'sub_tags="{sub_tags}"')
        if parent_tags:
            params.append(f'parent_tags="{parent_tags}"')
        if inherits:
            params.append(f'inherits_from="{inherits}"')

        return f"({', '.join(params)})" if params else ""

    def add_section(
        section_title: str,
        items: list[tuple[str, dict[str, Any]]],
        prefix: str = "",
    ) -> None:
        """Add a section to the document."""
        if not items:
            return

        doc.paragraph(f"<b>{section_title}</b>", style="Heading2")
        doc.spacer(height=3.0)

        for name, info in sorted(items):
            param_str = format_params(info)
            docline = (info.get("documentation") or "").split("\n")[0].strip()

            # Element name with params
            doc.paragraph(
                f"<b>{prefix}{name}</b>{param_str}",
                style="Code",
            )
            # Docstring if present
            if docline:
                doc.paragraph(f"    {docline}", style="Normal")

        doc.spacer(height=5.0)

    # Add sections
    add_section("Abstract Elements", abstracts, prefix="@")
    add_section("Elements", elements)
    add_section("Components", components)

    # Compile and render
    computed = doc.builder.compile(doc)
    pdf_bytes = doc.builder.render(computed)

    if destination:
        Path(destination).write_bytes(pdf_bytes)
        return None

    return pdf_bytes


def print_bag(
    bag: Any,
    destination: str | Path | None = None,
    title: str | None = None,
) -> bytes | None:
    """Generate PDF representation of a Bag using genro-print.

    Creates a formatted PDF document showing the Bag's hierarchical structure
    with node labels, values, and attributes.

    Requires genro-print to be installed.

    Args:
        bag: The Bag to print.
        destination: Optional file path to save the PDF. If None, returns bytes.
        title: Optional title. Defaults to "Bag Contents".

    Returns:
        PDF bytes if destination is None, otherwise None (file is written).

    Raises:
        ImportError: If genro-print is not installed.
    """
    try:
        from genro_print.builders import ReportLabBuilder
    except ImportError as e:
        msg = "genro-print required: pip install genro-print"
        raise ImportError(msg) from e

    from .bag import Bag

    doc_title = title or "Bag Contents"

    # Build PDF document
    doc = Bag(builder=ReportLabBuilder)
    doc.document(title=doc_title)

    # Title
    doc.paragraph(f"<b>{doc_title}</b>", style="Title")
    doc.spacer(height=5.0)

    def add_node(node: Any, depth: int = 0) -> None:
        """Add a node to the document recursively."""
        indent_str = "    " * depth
        tag = node.tag or ""
        label = node.label
        value = node.value

        # Format node line
        tag_str = f"[{tag}] " if tag else ""

        # Get attributes (excluding internal ones)
        attrs = {k: v for k, v in node.attr.items() if not k.startswith("_")}
        attr_str = ""
        if attrs:
            attr_parts = [f'{k}="{v}"' for k, v in attrs.items()]
            attr_str = f" ({', '.join(attr_parts)})"

        # Value display
        if isinstance(value, Bag):
            # Container node
            doc.paragraph(
                f"{indent_str}<b>{tag_str}{label}</b>{attr_str}",
                style="Normal",
            )
            # Recurse into children
            for child in value:
                add_node(child, depth + 1)
        else:
            # Leaf node with value
            value_str = f' = "{value}"' if value else ""
            doc.paragraph(
                f"{indent_str}<b>{tag_str}{label}</b>{value_str}{attr_str}",
                style="Normal",
            )

    # Add all nodes from the bag
    for node in bag:
        add_node(node, depth=0)

    # Compile and render
    computed = doc.builder.compile(doc)
    pdf_bytes = doc.builder.render(computed)

    if destination:
        Path(destination).write_bytes(pdf_bytes)
        return None

    return pdf_bytes
