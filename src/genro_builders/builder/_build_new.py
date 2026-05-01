# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""New build algorithm — rebuild from scratch.

Replaces ``_BuildMixin.build()`` for the HtmlBuilder. The legacy
``_BuildMixin`` stays alive for the other contrib builders.

Plain-html step: ``build()`` mirrors source nodes into the built tree,
copying tag, value, and attrs. Container values (sub-Bags) are
recreated as ``BuiltBagNew`` and walked recursively. Features beyond
plain html (pointers, callables, components, iterate, data elements)
are added one at a time.
"""

from __future__ import annotations

from typing import Any

from genro_bag import Bag, BagNode


class _BuiltBagMixin:
    """Helpers for the built bag. Empty — features added one at a time."""


class _BuiltNodeMixin:
    """Helpers for the built node. Features added one at a time."""

    @property
    def _is_data_element(self) -> bool:
        return False

    @property
    def runtime_value(self) -> Any:
        return self.get_value(static=True)

    @property
    def runtime_attrs(self) -> dict[str, Any]:
        attrs = dict(self.attr)
        attrs.pop("datapath", None)
        return attrs


class BuiltBagNodeNew(BagNode, _BuiltNodeMixin):
    pass


class BuiltBagNew(Bag, _BuiltBagMixin):
    node_class = BuiltBagNodeNew


class _BuildMixinNew:
    """New build mixin: replaces _BuildMixin's build() and new_built()."""

    def new_built(self) -> Bag:
        return BuiltBagNew()

    def build(self) -> Any:
        self.built.clear()
        self._mirror(self.source, self.built)

    def _mirror(self, src_bag: Bag, dst_bag: Bag) -> None:
        for src_node in src_bag:
            value = src_node.value
            if isinstance(value, Bag):
                dst_value = BuiltBagNew()
                Bag.set_item(
                    dst_bag,
                    src_node.label,
                    dst_value,
                    _attributes=dict(src_node.attr),
                    node_tag=src_node.node_tag,
                )
                self._mirror(value, dst_value)
            else:
                Bag.set_item(
                    dst_bag,
                    src_node.label,
                    value,
                    _attributes=dict(src_node.attr),
                    node_tag=src_node.node_tag,
                )
