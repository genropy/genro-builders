# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Builder system for genro-bag — grammar, validation, rendering, reactivity.

Define domain-specific grammars via decorators (@element, @abstract,
@component, @data_element) and build structured Bag hierarchies with
validation, reactive data binding, and computed data infrastructure.

A builder is a machine: it materializes a source Bag into a built Bag
in a two-pass walk (data elements first, then normal elements),
expanding components and keeping ^pointers formal (resolved just-in-time
during render/compile). A ``BuilderManager`` mixin coordinates one or
more builders with a shared reactive data store.

Lifecycle: setup (populate) -> build (materialize) -> subscribe (optional
reactivity) -> render/compile (output).

Core classes:
    BagBuilderBase: Grammar machine -- @element, @abstract, @component,
        @data_element, build, subscribe, render, compile.
        Data infrastructure: data_setter, data_formula, data_controller.
        Reactivity: topological sort, _delay (debounce), _interval
        (periodic), suspend_output / resume_output, computed attributes.
    BuilderBag: Bag subclass with grammar-first attribute resolution.
    BagRendererBase: Transform built Bag into serialized output (text, bytes).
    BagCompilerBase: Transform built Bag into live objects (widgets, etc.).
    BuilderManager: Sync coordinator for builders with shared data.
        Provides setup (store -> main), build, and run.
    ReactiveManager: Extends BuilderManager with subscribe() for
        reactive bindings (formula re-execution, _delay, _interval).
    BindingManager: Reactive ^pointer subscription map with 3-level
        propagation (node / container / child).
"""

from genro_builders.binding import (
    BindingManager,
    PointerInfo,
    is_pointer,
    parse_pointer,
    scan_for_pointers,
)
from genro_builders.builder import BagBuilderBase
from genro_builders.builder_bag import BuilderBag, BuilderBagNode, Component
from genro_builders.compiler import BagCompilerBase, compiler
from genro_builders.component_proxy import ComponentProxy
from genro_builders.component_resolver import ComponentResolver
from genro_builders.contrib.yaml import YamlRendererBase
from genro_builders.manager import BuilderManager
from genro_builders.reactive_manager import ReactiveManager
from genro_builders.renderer import BagRendererBase, RenderNode, renderer

__version__ = "0.16.0"

__all__ = [
    "BagBuilderBase",
    "BagCompilerBase",
    "BagRendererBase",
    "BindingManager",
    "BuilderBag",
    "BuilderBagNode",
    "BuilderManager",
    "Component",
    "ComponentProxy",
    "ComponentResolver",
    "PointerInfo",
    "ReactiveManager",
    "RenderNode",
    "YamlRendererBase",
    "compiler",
    "is_pointer",
    "parse_pointer",
    "renderer",
    "scan_for_pointers",
]
