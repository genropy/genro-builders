# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Builder package — re-exports all public and test-used symbols.

All external imports (``from genro_builders.builder import X``) continue
to work unchanged after the split from a single module to a package.
"""

from ._decorators import (
    abstract,
    data,
    data_controller,
    data_formula,
    element,
    struct_method,
    subbuilder,
)
from ._validators import Range, Regex
from .base import BagBuilderBase

__all__ = [
    "BagBuilderBase",
    "Range",
    "Regex",
    "abstract",
    "data",
    "data_controller",
    "data_formula",
    "element",
    "struct_method",
    "subbuilder",
]
