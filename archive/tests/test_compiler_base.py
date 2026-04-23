# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for BagCompilerBase — rendering via @compiler() dispatch.

Build walk is now in BagBuilderBase._build_walk(). These tests verify
the compiler's rendering infrastructure and the full build+render pipeline.
"""
from __future__ import annotations

from genro_bag import Bag

from genro_builders import BagBuilderBase, BagCompilerBase
from genro_builders.compiler import compiler
from genro_builders.builder._binding import BindingManager
from genro_builders.builder_bag import BuilderBag
from genro_builders.builder import component, element

# =============================================================================
# Test compiler with @compiler() for rendering
# =============================================================================


class TagCompiler(BagCompilerBase):
    """Compiler with @compiler() methods — handler(self, node, parent)."""

    @compiler()
    def heading(self, node, parent):
        return f"# {node.runtime_value or ''}"

    @compiler()
    def text(self, node, parent):
        return str(node.runtime_value or "")

    @compiler()
    def container(self, node, parent):
        node_value = node.get_value(static=True)
        if isinstance(node_value, Bag):
            children = list(self._walk_compile(node_value, parent=parent))
            return f"[{chr(10).join(str(c) for c in children)}]"
        return "[]"

    @compiler()
    def section(self, node, parent):
        node_value = node.get_value(static=True)
        if isinstance(node_value, Bag):
            children = list(self._walk_compile(node_value, parent=parent))
            return "\n".join(str(c) for c in children)
        return ""

    def render(self, compiled_bag):
        """Render using _walk_compile dispatch."""
        parts = list(self._walk_compile(compiled_bag))
        return "\n\n".join(str(p) for p in parts if p)


class TagBuilder(BagBuilderBase):


    @element()
    def heading(self): ...

    @element()
    def text(self): ...

    @element(sub_tags="text,heading")
    def container(self): ...

    @component()
    def section(self, comp, title=None, **kwargs):
        comp.heading(title or "Untitled")
        comp.text("body content")


def _build_walk(bag, data=None):
    """Helper: build walk from source bag into a new target."""
    builder = bag.builder
    target = BuilderBag(builder=TagBuilder)
    binding = BindingManager()
    if data is None:
        data = Bag()
    builder._build_walk(bag, target, data, binding)
    return target


def build_and_render(builder) -> str:
    """Helper: build walk → target → render to string via compiler."""
    target = BuilderBag(builder=TagBuilder)
    binding = BindingManager()
    builder._build_walk(builder._bag, target, Bag(), binding)
    compiler = TagCompiler(builder)
    return compiler.render(target)


# =============================================================================
# Tests for build walk → target Bag
# =============================================================================


class TestBuildWalkPopulatesTarget:
    """_build_walk() populates target Bag with expanded components and resolved pointers."""

    def test_build_walk_populates_target(self):
        """_build_walk() populates a target Bag."""
        bag = BuilderBag(builder=TagBuilder)
        bag.heading("Hello")

        built = _build_walk(bag)

        assert isinstance(built, Bag)
        assert built.get_node("heading_0") is not None

    def test_build_walk_expands_components(self):
        """Target has components expanded."""
        bag = BuilderBag(builder=TagBuilder)
        bag.section(title="Test")

        built = _build_walk(bag)

        section_node = built.get_node("section_0")
        assert section_node is not None
        assert isinstance(section_node.value, Bag)
        assert section_node.value.get_node("heading_0") is not None

    def test_build_walk_preserves_pointers_in_built(self):
        """Built keeps ^pointer strings — resolution happens at render time."""
        bag = BuilderBag(builder=TagBuilder)
        bag.heading("^title")

        data = Bag()
        data["title"] = "Resolved"

        built = _build_walk(bag, data=data)

        heading = built.get_node("heading_0")
        assert heading.static_value == "^title"

    def test_build_walk_without_data_keeps_pointers(self):
        """Without data, ^pointers remain as-is in target."""
        bag = BuilderBag(builder=TagBuilder)
        bag.heading("^title")

        built = _build_walk(bag)

        heading = built.get_node("heading_0")
        assert heading.static_value == "^title"


# =============================================================================
# Tests for rendering via _walk_compile
# =============================================================================


class TestRendering:
    """Tests for tag-based rendering via @compiler()."""

    def test_render_with_children(self):
        """Children rendered recursively."""
        bag = BuilderBag(builder=TagBuilder)
        container = bag.container()
        container.text("inside")

        result = build_and_render(bag.builder)
        assert "[inside]" in result

    def test_render_expanded_component(self):
        """Component is expanded, then rendered."""
        bag = BuilderBag(builder=TagBuilder)
        bag.section(title="My Section")

        result = build_and_render(bag.builder)

        assert "# My Section" in result
        assert "body content" in result


# =============================================================================
# Tests for default_compile
# =============================================================================


class TestDefaultCompile:
    """Tests for default_compile behavior."""

    def test_default_compile_recurses_children(self):
        """Default compile_node recurses — children get compiled too."""

        class NestBuilder(BagBuilderBase):
            @element(sub_tags="inner")
            def outer(self): ...

            @element()
            def inner(self): ...

        collected = []

        class Compiler(BagCompilerBase):
            def compile_node(self, node, parent=None, **kwargs):
                value = str(node.runtime_value or "")
                collected.append(value)
                return value or None

        bag = BuilderBag(builder=NestBuilder)
        outer = bag.outer()
        outer.inner("child content")

        target = BuilderBag(builder=NestBuilder)
        bag.builder._build_walk(bag, target, Bag(), BindingManager())
        comp = Compiler(bag.builder)

        list(comp._walk_compile(target))
        # Both outer (empty value) and inner ("child content") get visited
        assert "child content" in collected
