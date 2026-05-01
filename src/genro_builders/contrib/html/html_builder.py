# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""HtmlBuilder and HtmlRenderer - HTML5 element builder and renderer."""

from __future__ import annotations

from typing import Any

from genro_bag import Bag, BagNode

from ...builder import BagBuilderBase
from ...builder._build_new import _BuildMixinNew
from ...renderer import BagRendererBase, RenderNode
from .html5_elements import Html5Elements


class HtmlRenderer(BagRendererBase):
    """Renderer for HTML5 documents.

    Top-down: render_node returns a RenderNode for containers
    (nodes with children) or a plain string for leaves.
    Reads attributes directly from node.runtime_attrs.
    """

    _ATTR_MAP = {"_class": "class", "_style": "style", "_for": "for"}

    def render_node(
        self, node: BagNode,
        parent: list | None = None, **kwargs: Any,
    ) -> str | RenderNode | None:
        """Render a single node as HTML markup."""
        tag = node.node_tag or node.label
        attrs = node.runtime_attrs
        attrs_str_parts = []
        for k, v in attrs.items():
            if k.startswith("_"):
                html_name = self._ATTR_MAP.get(k)
                if html_name is None:
                    continue
                k = html_name
            attrs_str_parts.append(f'{k}="{v}"')
        attrs_str = f" {' '.join(attrs_str_parts)}" if attrs_str_parts else ""

        value = node.runtime_value
        node_value = "" if value is None or isinstance(value, Bag) else str(value)
        has_children = isinstance(node.get_value(static=True), Bag)

        if has_children:
            return RenderNode(
                before=f"<{tag}{attrs_str}>",
                after=f"</{tag}>",
                value=node_value,
                indent="  ",
            )

        if not node_value:
            return f"<{tag}{attrs_str}>"
        return f"<{tag}{attrs_str}>{node_value}</{tag}>"


class HtmlBuilder(_BuildMixinNew, BagBuilderBase, Html5Elements):
    """Builder for HTML5 elements."""

    _renderers = {"html": HtmlRenderer}
