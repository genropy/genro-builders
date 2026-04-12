# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Shared test fixtures: TestBuilder and TestRenderer."""
from __future__ import annotations

from typing import Any

from genro_bag import Bag, BagNode

from genro_builders.builder import BagBuilderBase, component, element
from genro_builders.renderer import BagRendererBase


class TestRenderer(BagRendererBase):
    """Simple renderer that produces [tag:value] notation for testing."""

    def render(self, built_bag: Bag, output: Any = None) -> str:
        parts = self._walk_render(built_bag)
        return "".join(p for p in parts if p)

    def render_node(
        self, node: BagNode, parent: list | None = None, **kwargs: Any,
    ) -> str | None:
        tag = node.node_tag or node.label
        resolved = node.evaluate_on_node(self.builder.data)
        value = resolved["node_value"]
        attrs = resolved["attrs"]
        has_children = isinstance(node.get_value(static=True), Bag)

        if has_children:
            from genro_builders.renderer import RenderNode
            rn = RenderNode(before=f"[{tag}:", after="]", separator="")
            return rn

        if value is not None:
            return f"[{tag}:{value}]"

        filtered = {k: v for k, v in attrs.items() if not k.startswith("_")}
        if filtered:
            attr_str = ",".join(f"{k}={v}" for k, v in filtered.items())
            return f"[{tag}:{attr_str}]"
        return f"[{tag}]"


class TestBuilder(BagBuilderBase):
    """Simple builder for testing."""

    _renderers = {"test": TestRenderer}

    @element()
    def heading(self): ...

    @element()
    def text(self): ...

    @element()
    def item(self): ...

    @component()
    def section(self, comp, title=None, **kwargs):
        comp.heading(title)
        comp.text("default content")
