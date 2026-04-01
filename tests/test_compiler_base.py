# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for BagCompilerBase — rendering via @compile_handler dispatch.

Build walk is now in BagBuilderBase._build_walk(). These tests verify
the compiler's rendering infrastructure and the full build+render pipeline.
"""
from __future__ import annotations

from genro_bag import Bag
from genro_builders import BagBuilderBase, BagCompilerBase, compile_handler
from genro_builders.binding import BindingManager
from genro_builders.builder_bag import BuilderBag
from genro_builders.builders import component, element


# =============================================================================
# Test compiler with @compile_handler for rendering
# =============================================================================


class TagCompiler(BagCompilerBase):
    """Compiler with @compile_handler methods for tag-based rendering."""

    @compile_handler
    def heading(self, node, ctx):
        return f"# {ctx['node_value']}"

    @compile_handler
    def text(self, node, ctx):
        return ctx["node_value"]

    @compile_handler
    def container(self, node, ctx):
        children = "\n".join(str(c) for c in ctx["children"]) if ctx["children"] else ""
        return f"[{children}]" if children else "[]"

    @compile_handler
    def section(self, node, ctx):
        return "\n".join(str(c) for c in ctx["children"]) if ctx["children"] else ""

    def render(self, compiled_bag):
        """Render using _walk_compile dispatch."""
        parts = list(self._walk_compile(compiled_bag))
        return "\n\n".join(str(p) for p in parts if p)


class TagBuilder(BagBuilderBase):
    _compiler_class = TagCompiler

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

    def test_build_walk_resolves_pointers(self):
        """Target has ^pointers resolved when data is provided."""
        bag = BuilderBag(builder=TagBuilder)
        bag.heading("^title")

        data = Bag()
        data["title"] = "Resolved"

        built = _build_walk(bag, data=data)

        heading = built.get_node("heading_0")
        assert heading.value == "Resolved"

    def test_build_walk_without_data_keeps_pointers(self):
        """Without data, ^pointers remain as-is in target."""
        bag = BuilderBag(builder=TagBuilder)
        bag.heading("^title")

        built = _build_walk(bag)

        heading = built.get_node("heading_0")
        assert heading.value == "^title"


# =============================================================================
# Tests for rendering via _walk_compile
# =============================================================================


class TestRendering:
    """Tests for tag-based rendering via @compile_handler."""

    def test_render_with_handlers(self):
        """@compile_handler methods render tags."""
        bag = BuilderBag(builder=TagBuilder)
        bag.heading("Hello")
        bag.text("World")

        result = build_and_render(bag.builder)

        assert "# Hello" in result
        assert "World" in result

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

    def test_default_compile_returns_value(self):
        """Node without handler uses default_compile — returns value."""

        class MinimalBuilder(BagBuilderBase):
            @element()
            def plain(self): ...

        class ConcreteCompiler(BagCompilerBase):
            def render(self, compiled_bag):
                parts = list(self._walk_compile(compiled_bag))
                return "\n\n".join(str(p) for p in parts if p)

        MinimalBuilder._compiler_class = ConcreteCompiler

        bag = BuilderBag(builder=MinimalBuilder)
        bag.plain("raw text")

        target = BuilderBag(builder=MinimalBuilder)
        bag.builder._build_walk(bag, target, Bag(), BindingManager())
        compiler = ConcreteCompiler(bag.builder)
        result = compiler.render(target)

        assert "raw text" in result

    def test_default_compile_returns_children(self):
        """default_compile returns children list if value is empty."""

        class NestBuilder(BagBuilderBase):
            @element(sub_tags="inner")
            def outer(self): ...

            @element()
            def inner(self): ...

        class Compiler(BagCompilerBase):
            pass

        NestBuilder._compiler_class = Compiler

        bag = BuilderBag(builder=NestBuilder)
        outer = bag.outer()
        outer.inner("child content")

        target = BuilderBag(builder=NestBuilder)
        bag.builder._build_walk(bag, target, Bag(), BindingManager())
        compiler = Compiler(bag.builder)

        # default_compile returns children list for parent nodes
        results = list(compiler._walk_compile(target))
        # outer's default_compile returns ["child content"] (list of children)
        assert any("child content" in str(r) for r in results)

    def test_default_compile_empty_node(self):
        """Empty node (no value, no children) produces nothing."""

        class EmptyBuilder(BagBuilderBase):
            @element()
            def empty(self): ...

        class Compiler(BagCompilerBase):
            def render(self, compiled_bag):
                parts = list(self._walk_compile(compiled_bag))
                return "\n\n".join(str(p) for p in parts if p)

        EmptyBuilder._compiler_class = Compiler

        bag = BuilderBag(builder=EmptyBuilder)
        bag.empty()

        target = BuilderBag(builder=EmptyBuilder)
        bag.builder._build_walk(bag, target, Bag(), BindingManager())
        compiler = Compiler(bag.builder)
        result = compiler.render(target)

        assert result == ""


# =============================================================================
# Tests for pointer resolution in build walk
# =============================================================================


class TestBuildWalkPointerResolution:
    """Tests for _build_walk resolving pointers."""

    def test_build_walk_with_data_resolves_pointers(self):
        """Data resolves ^pointers in target."""
        bag = BuilderBag(builder=TagBuilder)
        bag.heading("^title")
        bag.text("^body")

        data = Bag()
        data["title"] = "Resolved Title"
        data["body"] = "Resolved Body"

        target = BuilderBag(builder=TagBuilder)
        bag.builder._build_walk(bag, target, data, BindingManager())
        compiler = TagCompiler(bag.builder)
        result = compiler.render(target)

        assert "# Resolved Title" in result
        assert "Resolved Body" in result

    def test_build_walk_without_data_keeps_pointers(self):
        """Without data, ^pointers remain in rendering."""
        built = _build_walk(BuilderBag(builder=TagBuilder))
        bag = BuilderBag(builder=TagBuilder)
        bag.heading("^title")
        built = _build_walk(bag)
        compiler = TagCompiler(bag.builder)
        result = compiler.render(built)

        assert "^title" in result

    def test_build_walk_data_resolves_attr_pointers(self):
        """Data resolves ^pointers in attributes."""

        class AttrBuilder(BagBuilderBase):
            @element()
            def widget(self): ...

        class Compiler(BagCompilerBase):
            def render(self, compiled_bag):
                parts = list(self._walk_compile(compiled_bag))
                return "\n\n".join(str(p) for p in parts if p)

        AttrBuilder._compiler_class = Compiler

        bag = BuilderBag(builder=AttrBuilder)
        bag.widget(color="^theme.color")

        data = Bag()
        data["theme.color"] = "blue"

        target = BuilderBag(builder=AttrBuilder)
        bag.builder._build_walk(bag, target, data, BindingManager())

        widget = target.get_node("widget_0")
        assert widget.attr.get("color") == "blue"
