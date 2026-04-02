# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Builder system for genro-bag — grammar, validation, compilation, reactivity.

Define domain-specific grammars via decorators (@element, @abstract,
@component) and build structured Bag hierarchies with validation.

A builder owns the full reactive pipeline: source, built, data,
binding, and compiler. Optionally, a ``BuilderManager`` coordinates
multiple builders that share the same data bus.

Core classes:
    BagBuilderBase: Define grammars with @element, @abstract, @component.
    BuilderBag: Bag subclass with builder delegation.
    BagRendererBase: Transform built Bag into serialized output (text, bytes).
    BagCompilerBase: Transform built Bag into live objects (widgets, etc.).
    BuilderManager: Coordinate multiple builders with shared data.
    BindingManager: Reactive ^pointer subscription map.
"""

from genro_builders.binding import BindingManager
from genro_builders.builder import BagBuilderBase
from genro_builders.builder_bag import BuilderBag, BuilderBagNode
from genro_builders.compiler import BagCompilerBase, compile_handler
from genro_builders.compilers import YamlCompilerBase, YamlRendererBase
from genro_builders.component_proxy import ComponentProxy
from genro_builders.component_resolver import ComponentResolver
from genro_builders.manager import BuilderManager
from genro_builders.pointer import PointerInfo, is_pointer, parse_pointer
from genro_builders.renderer import BagRendererBase, render_handler

__version__ = "0.9.0"

__all__ = [
    "BagBuilderBase",
    "BagCompilerBase",
    "BagRendererBase",
    "BindingManager",
    "BuilderBag",
    "BuilderBagNode",
    "BuilderManager",
    "ComponentProxy",
    "ComponentResolver",
    "PointerInfo",
    "YamlCompilerBase",
    "YamlRendererBase",
    "compile_handler",
    "is_pointer",
    "render_handler",
    "parse_pointer",
]
