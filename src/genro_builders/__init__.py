# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Builder system for genro-bag — grammar, validation, rendering, reactivity.

Define domain-specific grammars via decorators (@element, @abstract,
@component, @data_element) and build structured Bag hierarchies with
validation, reactive data binding, and computed data infrastructure.

A builder is a machine: it materializes a source Bag into a built Bag
in a two-pass walk (data infrastructure first, then normal elements),
expanding components and keeping ^pointers formal (resolved just-in-time
during render/compile). A ``BuilderManager`` mixin coordinates one or
more builders with a shared reactive data store.

Pull-based reactivity: ``data_formula`` installs a ``FormulaResolver``
on the data store — values are computed on-demand when read.
Data changes signal dirty; the manager decides when to re-render/compile.

Lifecycle: setup (populate) -> build (materialize) -> subscribe (optional
reactivity) -> render/compile (output).

Core classes:
    BagBuilderBase: Grammar machine -- @element, @abstract, @component,
        @data_element, build, subscribe, render, compile.
        Data infrastructure: data_setter (static), data_formula (resolver).
    FormulaResolver: BagSyncResolver for pull-based computed data values.
    BuilderBag: Bag subclass with grammar-first attribute resolution.
    BagRendererBase: Transform built Bag into serialized output (text, bytes).
    BagCompilerBase: Transform built Bag into live objects (widgets, etc.).
    BuilderManager: Sync coordinator for builders with shared data.
    ReactiveManager: Extends BuilderManager with subscribe() for
        reactive bindings (data change tracking, incremental compile).
    BindingManager: Data change subscriber with UI node tracking.
"""

from genro_builders.builder import BagBuilderBase
from genro_builders.builder._binding import (
    BindingManager,
    PointerInfo,
    is_pointer,
    parse_pointer,
    scan_for_pointers,
)
from genro_builders.builder._component import ComponentProxy, ComponentResolver
from genro_builders.builder_bag import BuilderBag, BuilderBagNode, Component
from genro_builders.compiler import BagCompilerBase, compiler
from genro_builders.contrib.yaml import YamlRendererBase
from genro_builders.formula_resolver import FormulaResolver
from genro_builders.manager import BuilderManager, ReactiveManager
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
    "FormulaResolver",
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
