# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""HtmlBuilder and HtmlRenderer - HTML5 element builder and renderer.

The schema is defined as @element decorated methods in Html5Elements mixin,
generated from W3C Validator RELAX NG schema files.

Example:
    Creating an HTML document::

        from genro_builders.contrib.html import HtmlBuilder

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

import textwrap
from typing import Any

from genro_bag import BagNode

from ...builder import BagBuilderBase
from ...renderer import CTX_KEYS, BagRendererBase
from .html5_elements import Html5Elements


class HtmlRenderer(BagRendererBase):
    """Renderer for HTML5 documents.

    Uses the base class walk/dispatch/resolve infrastructure.
    Only render_node is overridden to produce HTML markup.
    """

    def render_node(
        self, node: BagNode, ctx: dict[str, Any],
        template: str | None = None, **kwargs: Any,
    ) -> str | None:
        """Render a single node as HTML markup."""
        tag = node.node_tag or node.label
        attrs = " ".join(
            f'{k}="{v}"'
            for k, v in ctx.items()
            if not k.startswith("_") and k not in CTX_KEYS
        )
        attrs_str = f" {attrs}" if attrs else ""

        node_value = ctx["node_value"]
        children = ctx["children"]

        if not children:
            if not node_value:
                return f"<{tag}{attrs_str}>"
            return f"<{tag}{attrs_str}>{node_value}</{tag}>"

        indented = textwrap.indent(children, "  ")
        return f"<{tag}{attrs_str}>\n{indented}\n</{tag}>"


class HtmlBuilder(BagBuilderBase, Html5Elements):
    """Builder for HTML5 elements.

    All 112 HTML5 elements are defined as @element methods in Html5Elements.
    """

    _renderers = {"html": HtmlRenderer}
