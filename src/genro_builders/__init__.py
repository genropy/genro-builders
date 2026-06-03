# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Builder system for genro-bag — grammar and bag layering.

Builders declare a domain-specific grammar via decorators
(@element, @abstract, @subbuilder, and @data_element for the three
data-elements data / data_formula / data_controller); BuilderHandlers
drive the create/render lifecycle on top of the grammar.

Core classes:
    BagBuilderBase: Grammar base — @element, @abstract,
        @subbuilder, @data_element.
    BuilderBag / BuilderBagNode: the bag/node pair. Contain the slots
        ``_builder`` and ``_handler`` and the grammar-aware attribute
        resolution. The handler populates a ``BuilderBag`` as
        ``self.source`` in ``handler.create()`` and serializes it in
        ``handler.render()``.
"""

from genro_builders.builder import BagBuilderBase, struct_method
from genro_builders.builder_bag import BuilderBag, BuilderBagNode

__version__ = "0.16.0"

__all__ = [
    "BagBuilderBase",
    "BuilderBag",
    "BuilderBagNode",
    "struct_method",
]
