# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""genro-builders: Builder system for genro-bag."""

from genro_builders.app import BagAppBase
from genro_builders.binding import BindingManager
from genro_builders.builder import BagBuilderBase
from genro_builders.builder_bag import BuilderBag, BuilderBagNode
from genro_builders.compiler import BagCompilerBase, compile_handler
from genro_builders.component_resolver import ComponentResolver
from genro_builders.pointer import PointerInfo, is_pointer, parse_pointer

__version__ = "0.2.0"

__all__ = [
    "BagAppBase",
    "BagBuilderBase",
    "BagCompilerBase",
    "BindingManager",
    "BuilderBag",
    "BuilderBagNode",
    "ComponentResolver",
    "PointerInfo",
    "compile_handler",
    "is_pointer",
    "parse_pointer",
]
