# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Core builder decorators, validators, and schema tools.

This module re-exports the core framework API. For concrete builders
(HTML, Markdown, XSD), import from ``genro_builders.contrib``:

    from genro_builders.contrib.html import HtmlBuilder
    from genro_builders.contrib.markdown import MarkdownBuilder
    from genro_builders.contrib.xsd import XsdBuilder

Core exports:
    - **BagBuilderBase**: Abstract base class for custom builders
    - **SchemaBuilder**: Builder for creating schemas programmatically
    - **element, abstract, component, data_element**: Grammar decorators
    - **Range, Regex**: Annotated-type validators
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

# Backward-compatible re-exports from contrib/ (deprecated paths)
from genro_builders.contrib.html import HtmlBuilder
from genro_builders.contrib.markdown import MarkdownBuilder
from genro_builders.contrib.xsd import XsdBuilder, XsdReader

__all__ = [
    "BagBuilderBase",
    "abstract",
    "component",
    "data_element",
    "element",
    "Range",
    "Regex",
    "HtmlBuilder",
    "MarkdownBuilder",
    "SchemaBuilder",
    "XsdBuilder",
    "XsdReader",
]
