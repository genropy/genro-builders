# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Builder utilities — helper functions for BagBuilderBase.

Provides ``quick_ref()`` for generating compact text summaries of a
builder's schema (elements, abstracts, components with parameters
and documentation). Kept as a separate module to avoid bloating the
builder package with presentation-only code.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

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

    for node in builder._schema:
        name = node.label
        info = builder._get_schema_info(name)

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
