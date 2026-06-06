# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""DataBuilderBase — base for structured data schemas.

A builder base without renderers or compilers. Its grammar defines data
structure, not presentation. Uses the standard ``@element`` mechanism.

The ``field`` element is the fundamental unit — a typed descriptor with
optional metadata (dtype, name_long, name_short, format, default).

Override ``on_configure()`` to declare the schema automatically at
registration time. Left unregistered (``_name = None``): it is a base to
subclass, not a usable dialect on its own.

Example:
    >>> class InvoiceData(DataBuilderBase):
    ...     def on_configure(self):
    ...         self.source.field("name", dtype="text", name_long="Customer Name")
    ...         self.source.field("vat", dtype="text", name_long="VAT Number")
"""
from __future__ import annotations

from typing import Any

from genro_builders.builder import BagBuilderBase
from genro_builders.builder._decorators import element


class DataBuilderBase(BagBuilderBase):
    """Base for structured data schemas.

    Defines data structure via ``field`` elements. No renderers or
    compilers — pure schema definition. Abstract anchor: left
    unregistered (``_name = None``), subclassed by concrete schemas.
    """

    _name = None

    @element()
    def field(
        self,
        dtype: str | None = None,
        name_long: str | None = None,
        name_short: str | None = None,
        format: str | None = None,
        default: Any = None,
    ): ...
