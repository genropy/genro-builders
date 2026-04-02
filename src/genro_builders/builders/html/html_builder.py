# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""HtmlBuilder and HtmlRenderer - HTML5 element builder and renderer.

The schema is defined as @element decorated methods in Html5Elements mixin,
generated from W3C Validator RELAX NG schema files.

Example:
    Creating an HTML document::

        from genro_builders.builders import HtmlBuilder

        b = HtmlBuilder()
        body = b.source.body()
        div = body.div(id='main', class_='container')
        div.h1(node_value='Welcome')
        div.p(node_value='Hello, World!')
        ul = div.ul()
        ul.li(node_value='Item 1')
        ul.li(node_value='Item 2')

        html = b.build()
"""

from __future__ import annotations

from typing import Any

from genro_bag import Bag, BagNode

from ...builder import BagBuilderBase
from ...renderer import BagRendererBase
from .html5_elements import Html5Elements


class HtmlRenderer(BagRendererBase):
    """Renderer for HTML5 documents."""

    def render(self, built_bag: Bag, output: Any = None) -> str:
        """Render the built Bag to HTML string."""
        lines = []
        for node in built_bag:
            lines.append(self._node_to_html(node, indent=0))
        return "\n".join(lines)

    def _node_to_html(self, node: BagNode, indent: int = 0) -> str:
        """Recursively convert a node to HTML."""
        tag = node.node_tag or node.label
        attrs = " ".join(f'{k}="{v}"' for k, v in node.attr.items() if not k.startswith("_"))
        attrs_str = f" {attrs}" if attrs else ""
        spaces = "  " * indent

        node_value = node.get_value(static=True)
        is_leaf = not isinstance(node_value, Bag)

        if is_leaf:
            if node_value == "" or node_value is None:
                return f"{spaces}<{tag}{attrs_str}>"
            return f"{spaces}<{tag}{attrs_str}>{node_value}</{tag}>"

        lines = [f"{spaces}<{tag}{attrs_str}>"]
        for child in node_value:
            lines.append(self._node_to_html(child, indent + 1))
        lines.append(f"{spaces}</{tag}>")
        return "\n".join(lines)


class HtmlBuilder(BagBuilderBase, Html5Elements):
    """Builder for HTML5 elements.

    All 112 HTML5 elements are defined as @element methods in Html5Elements.
    """

    _renderers = {"html": HtmlRenderer}
