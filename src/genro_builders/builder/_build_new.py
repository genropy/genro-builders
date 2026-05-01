# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""New build algorithm — rebuild from scratch.

Replaces ``_BuildMixin.build()`` for the HtmlBuilder. The legacy
``_BuildMixin`` stays alive for the other contrib builders.

Step (a): ``build()`` is a no-op. ``new_built()`` returns a fresh
``BuiltBagNew`` instance. Features are added one at a time on the
mixins below.
"""

from __future__ import annotations

from typing import Any

from genro_bag import Bag, BagNode


class _BuiltBagMixin:
    """Helpers for the built bag. Empty — features added one at a time."""


class _BuiltNodeMixin:
    """Helpers for the built node. Empty — features added one at a time."""


class BuiltBagNodeNew(BagNode, _BuiltNodeMixin):
    pass


class BuiltBagNew(Bag, _BuiltBagMixin):
    node_class = BuiltBagNodeNew


class _BuildMixinNew:
    """New build mixin: replaces _BuildMixin's build() and new_built()."""

    def new_built(self) -> Bag:
        return BuiltBagNew()

    def build(self) -> Any:
        pass
