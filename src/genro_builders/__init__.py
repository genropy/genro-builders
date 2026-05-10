# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Builder system for genro-bag — grammar and bag layering.

Builders declare a domain-specific grammar via decorators
(@element, @abstract, @component); BuilderHandlers (introduced
during fase 2 of the 2026-05 restart) drive the create/build/render
lifecycle on top of the grammar.

Core classes:
    BagBuilderBase: Grammar base — @element, @abstract, @component.
    BuilderBag / BuilderBagNode: level 1 of the bag/node layering
        (decision 12). Contain the slots ``_builder`` and ``_handler``
        and the grammar-aware attribute resolution shared between
        source and built.
    BuilderSourceBag / BuilderSourceBagNode: level 2 source side.
    BuilderBuiltBag / BuilderBuiltBagNode: level 2 built side.
"""

from genro_builders.builder import BagBuilderBase
from genro_builders.builder_bag import BuilderBag, BuilderBagNode
from genro_builders.built_bag import (
    BuilderBuiltBag,
    BuilderBuiltBagNode,
    BuilderSourceBag,
    BuilderSourceBagNode,
)

__version__ = "0.16.0"

__all__ = [
    "BagBuilderBase",
    "BuilderBag",
    "BuilderBagNode",
    "BuilderBuiltBag",
    "BuilderBuiltBagNode",
    "BuilderSourceBag",
    "BuilderSourceBagNode",
]
