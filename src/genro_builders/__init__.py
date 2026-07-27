# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Builder system for genro-bag — grammar and bag layering.

Builders declare a domain-specific grammar via decorators (@element,
@abstract). Sub-builders and data-elements are ordinary @element marked
in their ``_meta`` (``subbuilder`` / ``data_element``). A builder is also
the document: it owns the create/render lifecycle on top of its grammar.

Core classes:
    BuilderBase: Grammar base — @element, @abstract (sub-builders and
        data-elements are @element with the matching ``_meta`` marker).
        ``create()`` populates ``self.source``, ``render()`` serializes
        it through the renderer of the requested mode.
    SourceBag / SourceBagNode: the bag/node pair. Contain the slots
        ``_builder`` and ``_handler`` and the grammar-aware attribute
        resolution.

A builder that reads pointers is mounted on a ``BuilderHandler``, which
supplies the data and does not render.
"""

from genro_builders.builder import BuilderBase, SourceBag, SourceBagNode, container

__version__ = "0.20.0"

__all__ = [
    "BuilderBase",
    "SourceBag",
    "SourceBagNode",
    "container",
]
