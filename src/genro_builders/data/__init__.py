# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""DataBuilderBase — structured data definition via builder grammar.

Provides a builder base for defining data schemas using the standard
``@element`` mechanism. Fields are typed descriptors. It is a base
(``_name = None``), subclassed by concrete schemas — not a dialect.

Example:
    >>> from genro_builders.data import DataBuilderBase
    >>>
    >>> class InvoiceData(DataBuilderBase):
    ...     def on_configure(self):
    ...         self.source.field("name", dtype="text", name_long="Customer Name")
    ...         self.source.field("vat", dtype="text", name_long="VAT Number")
"""

from .data_builder import DataBuilderBase

__all__ = ["DataBuilderBase"]
