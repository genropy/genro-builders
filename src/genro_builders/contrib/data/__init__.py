# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""DataBuilder — structured data definition via builder grammar.

Provides a builder for defining data schemas using the same element/component
mechanism as presentation builders. Fields are typed descriptors; components
group related fields for reuse.

Example:
    >>> from genro_builders.contrib.data import DataBuilder
    >>>
    >>> class InvoiceData(DataBuilder):
    ...     @component()
    ...     def customer(self, comp):
    ...         comp.field("name", dtype="text", name_long="Customer Name")
    ...         comp.field("vat", dtype="text", name_long="VAT Number")
"""

from .data_builder import DataBuilder

__all__ = ["DataBuilder"]
