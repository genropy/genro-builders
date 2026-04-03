# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Builder system for genro-bag — grammar, validation, rendering, reactivity.

Define domain-specific grammars via decorators (@element, @abstract,
@component) and build structured Bag hierarchies with validation.

A builder is a machine: it materializes a source Bag into a built Bag,
expanding components and resolving ^pointers. A ``BuilderManager`` mixin
coordinates one or more builders with a shared reactive data store.

Lifecycle: setup (populate) → build (materialize) → subscribe (optional
reactivity) → render/compile (output).

Core classes:
    BagBuilderBase: Grammar machine — @element, @abstract, @component,
        build, subscribe, render, compile.
    BuilderBag: Bag subclass with grammar-first attribute resolution.
    BagRendererBase: Transform built Bag into serialized output (text, bytes).
    BagCompilerBase: Transform built Bag into live objects (widgets, etc.).
    BuilderManager: Mixin to coordinate builders with shared data.
        Provides setup (store → main), build, and subscribe.
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
