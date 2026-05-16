# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Level-2 bag/node specialization for the source (decision 12 v0.4.0).

The handler instantiates ``BuilderSource`` as the bag the user
populates in ``handler.create()`` and that ``handler.render()``
serializes. It is an empty subclass for now: it exists as extension
point and as discriminating type for the source role. Mixins
specific to source will be added when needed.

Future specializations (e.g. ``BuilderData`` for the builder data
bag) will mirror this pattern.
"""
from __future__ import annotations

from genro_bag import BagNode

from .builder_bag import BuilderBag, BuilderBagNode


class BuilderSourceNode(BuilderBagNode):
    """Source-side node. Inherits grammar dispatch from level 1."""

    __slots__ = ()


class BuilderSource(BuilderBag):
    """Source-side bag. The user populates this through ``handler.create()``."""

    node_class: type[BagNode] = BuilderSourceNode
