# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""DataBuilder — structured data definition via builder grammar.

Provides a builder for defining data schemas using the standard
``@element`` mechanism. Fields are typed descriptors.

Example:
    >>> from genro_builders.contrib.data import DataBuilder
    >>>
    >>> class InvoiceData(DataBuilder):
    ...     def on_configure(self):
    ...         self.source.field("name", dtype="text", name_long="Customer Name")
    ...         self.source.field("vat", dtype="text", name_long="VAT Number")
"""

from .data_builder import DataBuilder

__all__ = ["DataBuilder"]
