# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Core builder decorators, validators, and schema tools.

For concrete builders, import from ``genro_builders.contrib``:

    from genro_builders.contrib.html import HtmlBuilder
    from genro_builders.contrib.markdown import MarkdownBuilder
    from genro_builders.contrib.xsd import XsdBuilder
"""

from genro_builders.builder import (
    BagBuilderBase,
    Range,
    Regex,
    SchemaBuilder,
    abstract,
    component,
    data_element,
    element,
)

__all__ = [
    "BagBuilderBase",
    "Range",
    "Regex",
    "SchemaBuilder",
    "abstract",
    "component",
    "data_element",
    "element",
]
