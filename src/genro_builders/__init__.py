# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Builder system for genro-bag — grammar and bag layering.

Builders declare a domain-specific grammar via decorators
(@element, @abstract, @subbuilder, @data_element); BuilderHandlers
drive the create/render lifecycle on top of the grammar.

Core classes:
    BagBuilderBase: Grammar base — @element, @abstract,
        @subbuilder, @data_element.
    BuilderBag / BuilderBagNode: level 1 of the bag/node layering
        (decision 12). Contain the slots ``_builder`` and ``_handler``
        and the grammar-aware attribute resolution shared between
        specializations.
    BuilderSource / BuilderSourceNode: level 2 source side, the bag
        the user populates in ``handler.create()`` and that
        ``handler.render()`` serializes.
"""

from genro_builders.builder import BagBuilderBase, struct_method
from genro_builders.builder_bag import BuilderBag, BuilderBagNode
from genro_builders.source_bag import BuilderSource, BuilderSourceNode

__version__ = "0.16.0"

__all__ = [
    "BagBuilderBase",
    "BuilderBag",
    "BuilderBagNode",
    "BuilderSource",
    "BuilderSourceNode",
    "struct_method",
]
