# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Builder package — re-exports all public and test-used symbols.

All external imports (``from genro_builders.builder import X``) continue
to work unchanged after the split from a single module to a package.
"""

from ._decorators import abstract, component, data_element, element
from ._schema_builder import SchemaBuilder
from ._utilities import (
    _check_type,
    _parse_sub_tags_spec,
    _split_annotated,
)
from ._validators import Range, Regex
from .base import BagBuilderBase

__all__ = [
    "BagBuilderBase",
    "SchemaBuilder",
    "element",
    "abstract",
    "component",
    "data_element",
    "Regex",
    "Range",
    "_check_type",
    "_parse_sub_tags_spec",
    "_split_annotated",
]
