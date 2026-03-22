# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for BagCompilerBase — compile() returns CompiledBag, rendering is separate."""
from __future__ import annotations

from genro_bag import Bag
from genro_builders import BagBuilderBase, BagCompilerBase, compile_handler
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
        return f"[{ctx['children']}]" if ctx["children"] else "[]"

    @compile_handler
    def section(self, node, ctx):
        return ctx["children"]

    def render(self, compiled_bag):
        """Render using _walk_compile dispatch."""
        parts = list(self._walk_compile(compiled_bag))
        return "\n\n".join(p for p in parts if p)


class TagBuilder(BagBuilderBase):
    compiler_class = TagCompiler

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


def compile_and_render(builder) -> str:
    """Helper: compile bag → CompiledBag → render to string."""
    compiler = builder.compiler
    compiled = compiler.compile(builder.bag)
    return compiler.render(compiled)


# =============================================================================
# Tests for compile() → CompiledBag
# =============================================================================


class TestCompileReturnsCompiledBag:
    """compile() returns a Bag (CompiledBag), not a string."""

    def test_compile_returns_bag(self):
        """compile() returns a Bag instance."""
        bag = BuilderBag(builder=TagBuilder)
        bag.heading("Hello")

        compiler = TagCompiler(bag.builder)
        result = compiler.compile(bag)

        assert isinstance(result, Bag)

    def test_compiled_bag_has_expanded_components(self):
        """CompiledBag has components expanded."""
        bag = BuilderBag(builder=TagBuilder)
        bag.section(title="Test")

        compiler = TagCompiler(bag.builder)
        compiled = compiler.compile(bag)

        # The section should be expanded — its children visible
        section_node = compiled.get_node("section_0")
        assert section_node is not None
        assert isinstance(section_node.value, Bag)
        assert section_node.value.get_node("heading_0") is not None

    def test_compiled_bag_has_resolved_pointers(self):
        """CompiledBag has ^pointers resolved when data is provided."""
        bag = BuilderBag(builder=TagBuilder)
        bag.heading("^title")

        data = Bag()
        data["title"] = "Resolved"

        compiler = TagCompiler(bag.builder)
        compiled = compiler.compile(bag, data=data)

        heading = compiled.get_node("heading_0")
        assert heading.value == "Resolved"

    def test_compile_without_data_keeps_pointers(self):
        """Without data, ^pointers remain as-is in CompiledBag."""
        bag = BuilderBag(builder=TagBuilder)
        bag.heading("^title")

        compiler = TagCompiler(bag.builder)
        compiled = compiler.compile(bag)

        heading = compiled.get_node("heading_0")
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

        result = compile_and_render(bag.builder)

        assert "# Hello" in result
        assert "World" in result

    def test_render_with_children(self):
        """Children rendered recursively."""
        bag = BuilderBag(builder=TagBuilder)
        container = bag.container()
        container.text("inside")

        result = compile_and_render(bag.builder)
        assert "[inside]" in result

    def test_render_expanded_component(self):
        """Component is expanded, then rendered."""
        bag = BuilderBag(builder=TagBuilder)
        bag.section(title="My Section")

        result = compile_and_render(bag.builder)

        assert "# My Section" in result
        assert "body content" in result


# =============================================================================
# Tests for default_compile
# =============================================================================


class TestDefaultCompile:
    """Tests for default_compile with templates and callbacks."""

    def test_default_compile_returns_value(self):
        """Node without handler uses default_compile — returns value."""

        class MinimalBuilder(BagBuilderBase):
            @element()
            def plain(self): ...

        class ConcreteCompiler(BagCompilerBase):
            def render(self, compiled_bag):
                parts = list(self._walk_compile(compiled_bag))
                return "\n\n".join(p for p in parts if p)

        MinimalBuilder.compiler_class = ConcreteCompiler

        bag = BuilderBag(builder=MinimalBuilder)
        bag.plain("raw text")

        compiler = ConcreteCompiler(bag.builder)
        compiled = compiler.compile(bag)
        result = compiler.render(compiled)

        assert "raw text" in result

    def test_compile_template(self):
        """compile_kwargs with template formats the output."""

        class TemplateBuilder(BagBuilderBase):
            @element(compile_template="<{node_label}>{node_value}</{node_label}>")
            def tag(self): ...

        class Compiler(BagCompilerBase):
            def render(self, compiled_bag):
                parts = list(self._walk_compile(compiled_bag))
                return "\n\n".join(p for p in parts if p)

        TemplateBuilder.compiler_class = Compiler

        bag = BuilderBag(builder=TemplateBuilder)
        bag.tag("content")

        compiler = Compiler(bag.builder)
        compiled = compiler.compile(bag)
        result = compiler.render(compiled)

        assert "<tag_0>content</tag_0>" in result

    def test_compile_template_missing_key(self):
        """Template with missing placeholder returns template as-is."""

        class BadTemplateBuilder(BagBuilderBase):
            @element(compile_template="{missing_key}")
            def tag(self): ...

        class Compiler(BagCompilerBase):
            def render(self, compiled_bag):
                parts = list(self._walk_compile(compiled_bag))
                return "\n\n".join(p for p in parts if p)

        BadTemplateBuilder.compiler_class = Compiler

        bag = BuilderBag(builder=BadTemplateBuilder)
        bag.tag("value")

        compiler = Compiler(bag.builder)
        compiled = compiler.compile(bag)
        result = compiler.render(compiled)

        assert "{missing_key}" in result

    def test_compile_callback(self):
        """compile_kwargs with callback modifies context."""

        class CbBuilder(BagBuilderBase):
            @element(compile_callback="uppercase_value", compile_template="{node_value}")
            def tag(self): ...

        class CbCompiler(BagCompilerBase):
            def uppercase_value(self, ctx):
                ctx["node_value"] = ctx["node_value"].upper()

            def render(self, compiled_bag):
                parts = list(self._walk_compile(compiled_bag))
                return "\n\n".join(p for p in parts if p)

        CbBuilder.compiler_class = CbCompiler

        bag = BuilderBag(builder=CbBuilder)
        bag.tag("hello")

        compiler = CbCompiler(bag.builder)
        compiled = compiler.compile(bag)
        result = compiler.render(compiled)

        assert "HELLO" in result

    def test_default_compile_returns_children(self):
        """default_compile returns children if value is empty."""

        class NestBuilder(BagBuilderBase):
            @element(sub_tags="inner")
            def outer(self): ...

            @element()
            def inner(self): ...

        class Compiler(BagCompilerBase):
            def render(self, compiled_bag):
                parts = list(self._walk_compile(compiled_bag))
                return "\n\n".join(p for p in parts if p)

        NestBuilder.compiler_class = Compiler

        bag = BuilderBag(builder=NestBuilder)
        outer = bag.outer()
        outer.inner("child content")

        compiler = Compiler(bag.builder)
        compiled = compiler.compile(bag)
        result = compiler.render(compiled)

        assert "child content" in result

    def test_default_compile_empty_node(self):
        """Empty node (no value, no children) produces nothing."""

        class EmptyBuilder(BagBuilderBase):
            @element()
            def empty(self): ...

        class Compiler(BagCompilerBase):
            def render(self, compiled_bag):
                parts = list(self._walk_compile(compiled_bag))
                return "\n\n".join(p for p in parts if p)

        EmptyBuilder.compiler_class = Compiler

        bag = BuilderBag(builder=EmptyBuilder)
        bag.empty()

        compiler = Compiler(bag.builder)
        compiled = compiler.compile(bag)
        result = compiler.render(compiled)

        assert result == ""


# =============================================================================
# Tests for script-mode pointer resolution in compile()
# =============================================================================


class TestScriptModeCompile:
    """Tests for compiler.compile(data=data) resolving pointers."""

    def test_compile_with_data_resolves_pointers(self):
        """Data resolves ^pointers in CompiledBag."""
        bag = BuilderBag(builder=TagBuilder)
        bag.heading("^title")
        bag.text("^body")

        data = Bag()
        data["title"] = "Resolved Title"
        data["body"] = "Resolved Body"

        compiler = TagCompiler(bag.builder)
        compiled = compiler.compile(bag, data=data)
        result = compiler.render(compiled)

        assert "# Resolved Title" in result
        assert "Resolved Body" in result

    def test_compile_without_data_keeps_pointers(self):
        """Without data, ^pointers remain in rendering."""
        bag = BuilderBag(builder=TagBuilder)
        bag.heading("^title")

        compiler = TagCompiler(bag.builder)
        compiled = compiler.compile(bag)
        result = compiler.render(compiled)

        assert "^title" in result

    def test_compile_data_resolves_attr_pointers(self):
        """Data resolves ^pointers in attributes."""

        class AttrBuilder(BagBuilderBase):
            @element(compile_template="color={color}")
            def widget(self): ...

        class Compiler(BagCompilerBase):
            def render(self, compiled_bag):
                parts = list(self._walk_compile(compiled_bag))
                return "\n\n".join(p for p in parts if p)

        AttrBuilder.compiler_class = Compiler

        bag = BuilderBag(builder=AttrBuilder)
        bag.widget(color="^theme.color")

        data = Bag()
        data["theme.color"] = "blue"

        compiler = Compiler(bag.builder)
        compiled = compiler.compile(bag, data=data)
        result = compiler.render(compiled)

        assert "color=blue" in result
