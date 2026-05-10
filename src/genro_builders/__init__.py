# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Builder system for genro-bag — grammar and bag layering.

Builders declare a domain-specific grammar via decorators
(@element, @abstract, @component); BuilderHandlers (introduced
during fase 2 of the 2026-05 restart) drive the create/build/render
lifecycle on top of the grammar.

Core classes (fase 1):
    BagBuilderBase: Grammar base — @element, @abstract, @component.
    BuilderBag / BuilderBagNode: Bag subclasses with grammar-aware
        attribute resolution. Layering refinement (decision 12,
        BuilderSourceBag/BuilderBuiltBag) lands in fase 2.
    Component: Bag passed to @component handlers.
    ComponentProxy: Proxy returned by component calls (fluent chain).
"""

from genro_builders.builder import BagBuilderBase
from genro_builders.builder._component import ComponentProxy
from genro_builders.builder_bag import BuilderBag, BuilderBagNode, Component

__version__ = "0.16.0"

__all__ = [
    "BagBuilderBase",
    "BuilderBag",
    "BuilderBagNode",
    "Component",
    "ComponentProxy",
]
