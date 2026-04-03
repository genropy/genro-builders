# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Shared test fixtures: TestBuilder and TestCompiler."""
from __future__ import annotations

from genro_bag import Bag

from genro_builders.builder import BagBuilderBase, component, element
from genro_builders.compiler import BagCompilerBase


class TestBuilder(BagBuilderBase):
    """Simple builder for testing."""

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


class TestCompiler(BagCompilerBase):
    """Simple compiler that renders tags with resolved values."""

    def render(self, compiled_bag):
        return self._render_bag(compiled_bag)

    def _render_bag(self, bag):
        parts = []
        for node in bag:
            tag = node.node_tag or node.label
            resolved = self.builder._resolve_node(node, self.builder.data)
            value = resolved["node_value"]
            attrs = resolved["attrs"]
            if isinstance(value, Bag):
                children = self._render_bag(value)
                parts.append(f"[{tag}:{children}]")
            elif value is not None:
                parts.append(f"[{tag}:{value}]")
            else:
                filtered = {k: v for k, v in attrs.items() if not k.startswith("_")}
                if filtered:
                    attr_str = ",".join(f"{k}={v}" for k, v in filtered.items())
                    parts.append(f"[{tag}:{attr_str}]")
                else:
                    parts.append(f"[{tag}]")
        return "".join(parts)


TestBuilder._compiler_class = TestCompiler
