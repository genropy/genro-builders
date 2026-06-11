# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Builder package — re-exports all public and test-used symbols.

All external imports (``from genro_builders.builder import X``) continue
to work unchanged after the split from a single module to a package.
"""

from ._decorators import (
    abstract,
    component,
    element,
    container,
)
from ._validators import Range, Regex
from .base import BuilderBase
from .data_handler import BuilderHandler, live
from .source_bag import SourceBag, SourceBagNode
from .target_wrapper import TargetWrapper

__all__ = [
    "BuilderBase",
    "SourceBag",
    "SourceBagNode",
    "BuilderHandler",
    "TargetWrapper",
    "live",
    "Range",
    "Regex",
    "abstract",
    "component",
    "element",
    "container",
]
