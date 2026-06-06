# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Builder system for genro-bag — grammar and bag layering.

Builders declare a domain-specific grammar via decorators (@element,
@abstract). Sub-builders and data-elements are ordinary @element marked
in their ``_meta`` (``subbuilder`` / ``data_element``); BuilderHandlers
drive the create/render lifecycle on top of the grammar.

Core classes:
    BuilderBase: Grammar base — @element, @abstract (sub-builders and
        data-elements are @element with the matching ``_meta`` marker).
    SourceBag / SourceBagNode: the bag/node pair. Contain the slots
        ``_builder`` and ``_handler`` and the grammar-aware attribute
        resolution. The handler populates a ``SourceBag`` as
        ``self.source`` in ``handler.create()`` and serializes it in
        ``handler.render()``.
"""

from genro_builders.builder import BuilderBase, SourceBag, SourceBagNode, struct_method

__version__ = "0.16.0"

__all__ = [
    "BuilderBase",
    "SourceBag",
    "SourceBagNode",
    "struct_method",
]
