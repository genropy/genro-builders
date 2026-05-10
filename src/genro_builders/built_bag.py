# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Level-2 bag/node specialization (decision 12).

The handler instantiates ``BuilderSourceBag`` for the user-facing
recipe and ``BuilderBuiltBag`` for the materialized tree. They are
empty subclasses for now: they exist as extension points and as
discriminating types between the two phases (decision 12). Mixins
specific to source or built will be added when needed.
"""
from __future__ import annotations

from genro_bag import BagNode

from .builder_bag import BuilderBag, BuilderBagNode


class BuilderSourceBagNode(BuilderBagNode):
    """Source-side node. Inherits grammar dispatch from level 1."""

    __slots__ = ()


class BuilderSourceBag(BuilderBag):
    """Source-side bag. The user populates this through ``handler.create()``."""

    node_class: type[BagNode] = BuilderSourceBagNode


class BuilderBuiltBagNode(BuilderBagNode):
    """Built-side node. Pure container during fase 2.3."""

    __slots__ = ()


class BuilderBuiltBag(BuilderBag):
    """Built-side bag. The builder populates this during ``handler.build()``."""

    node_class: type[BagNode] = BuilderBuiltBagNode
