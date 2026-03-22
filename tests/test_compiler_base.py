# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for BagCompilerBase methods — compile, default_compile, script mode."""
from __future__ import annotations

from genro_bag import Bag
from genro_builders import BagBuilderBase, BagCompilerBase, compile_handler
from genro_builders.builder_bag import BuilderBag
from genro_builders.builders import component, element


# =============================================================================
# Test compiler using the BASE compile() flow
# =============================================================================


class TagCompiler(BagCompilerBase):
    """Compiler that uses the base compile() flow with @compile_handler."""

    @compile_handler
    def heading(self, node, ctx):
        return f"# {ctx['node_value']}"

    @compile_handler
    def text(self, node, ctx):
        return ctx["node_value"]

    @compile_handler
    def container(self, node, ctx):
        return f"[{ctx['children']}]" if ctx["children"] else "[]"


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


class TestBaseCompile:
    """Tests for BagCompilerBase.compile() base flow."""

    def test_compile_with_bag(self):
        """compile(bag) uses the base flow: preprocess + walk + join."""
        bag = BuilderBag(builder=TagBuilder)
        bag.heading("Hello")
        bag.text("World")

        compiler = TagCompiler(bag.builder)
        result = compiler.compile(bag)

        assert "# Hello" in result
        assert "World" in result

    def test_compile_without_bag_uses_builder_bag(self):
        """compile() without bag uses builder.bag."""
        bag = BuilderBag(builder=TagBuilder)
        bag.heading("Test")

        compiler = TagCompiler(bag.builder)
        result = compiler.compile()

        assert "# Test" in result

    def test_compile_with_children(self):
        """Nodes with Bag children compile children recursively."""
        bag = BuilderBag(builder=TagBuilder)
        container = bag.container()
        container.text("inside")

        compiler = TagCompiler(bag.builder)
        result = compiler.compile(bag)

        assert "[inside]" in result

    def test_compile_with_component(self):
        """Components are expanded during compile via preprocess."""

        class SectionCompiler(BagCompilerBase):
            @compile_handler
            def heading(self, node, ctx):
                return f"# {ctx['node_value']}"

            @compile_handler
            def text(self, node, ctx):
                return ctx["node_value"]

            @compile_handler
            def section(self, node, ctx):
                return ctx["children"]

        bag = BuilderBag(builder=TagBuilder)
        bag.section(title="My Section")

        compiler = SectionCompiler(bag.builder)
        result = compiler.compile(bag)

        assert "# My Section" in result
        assert "body content" in result


class TestDefaultCompile:
    """Tests for default_compile with templates and callbacks."""

    def test_default_compile_returns_value(self):
        """Node without handler uses default_compile — returns value."""

        class MinimalBuilder(BagBuilderBase):
            compiler_class = BagCompilerBase

            @element()
            def plain(self): ...

        bag = BuilderBag(builder=MinimalBuilder)
        bag.plain("raw text")

        # Use a concrete subclass since BagCompilerBase is ABC
        class ConcreteCompiler(BagCompilerBase):
            pass

        compiler = ConcreteCompiler(bag.builder)
        result = compiler.compile(bag)

        assert "raw text" in result

    def test_compile_template(self):
        """compile_kwargs with template formats the output."""

        class TemplateBuilder(BagBuilderBase):
            @element(compile_template="<{node_label}>{node_value}</{node_label}>")
            def tag(self): ...

        class TemplateCompiler(BagCompilerBase):
            pass

        bag = BuilderBag(builder=TemplateBuilder)
        bag.tag("content")

        compiler = TemplateCompiler(bag.builder)
        result = compiler.compile(bag)

        assert "<tag_0>content</tag_0>" in result

    def test_compile_template_missing_key(self):
        """Template with missing placeholder returns template as-is."""

        class BadTemplateBuilder(BagBuilderBase):
            @element(compile_template="{missing_key}")
            def tag(self): ...

        class Compiler(BagCompilerBase):
            pass

        bag = BuilderBag(builder=BadTemplateBuilder)
        bag.tag("value")

        compiler = Compiler(bag.builder)
        result = compiler.compile(bag)

        assert "{missing_key}" in result

    def test_compile_callback(self):
        """compile_kwargs with callback modifies context."""

        class CbBuilder(BagBuilderBase):
            @element(compile_callback="uppercase_value", compile_template="{node_value}")
            def tag(self): ...

        class CbCompiler(BagCompilerBase):
            def uppercase_value(self, ctx):
                ctx["node_value"] = ctx["node_value"].upper()

        bag = BuilderBag(builder=CbBuilder)
        bag.tag("hello")

        compiler = CbCompiler(bag.builder)
        result = compiler.compile(bag)

        assert "HELLO" in result

    def test_default_compile_returns_children(self):
        """default_compile returns children if value is empty."""

        class NestBuilder(BagBuilderBase):
            @element(sub_tags="inner")
            def outer(self): ...

            @element()
            def inner(self): ...

        class Compiler(BagCompilerBase):
            pass

        bag = BuilderBag(builder=NestBuilder)
        outer = bag.outer()
        outer.inner("child content")

        compiler = Compiler(bag.builder)
        result = compiler.compile(bag)

        assert "child content" in result

    def test_default_compile_empty_node_returns_none(self):
        """Empty node (no value, no children) produces nothing."""

        class EmptyBuilder(BagBuilderBase):
            @element()
            def empty(self): ...

        class Compiler(BagCompilerBase):
            pass

        bag = BuilderBag(builder=EmptyBuilder)
        bag.empty()

        compiler = Compiler(bag.builder)
        result = compiler.compile(bag)

        assert result == ""


class TestScriptModeCompile:
    """Tests for compiler.compile(data=data) script mode."""

    def test_compile_with_data_resolves_pointers(self):
        """Script mode resolves ^pointers inline."""
        bag = BuilderBag(builder=TagBuilder)
        bag.heading("^title")
        bag.text("^body")

        data = Bag()
        data["title"] = "Resolved Title"
        data["body"] = "Resolved Body"

        compiler = TagCompiler(bag.builder)
        result = compiler.compile(bag, data=data)

        assert "# Resolved Title" in result
        assert "Resolved Body" in result

    def test_compile_without_data_leaves_pointers(self):
        """Without data, ^pointers remain as strings."""
        bag = BuilderBag(builder=TagBuilder)
        bag.heading("^title")

        compiler = TagCompiler(bag.builder)
        result = compiler.compile(bag)

        assert "^title" in result

    def test_compile_data_resolves_attr_pointers(self):
        """Script mode resolves ^pointers in attributes too."""

        class AttrBuilder(BagBuilderBase):
            @element(compile_template="color={color}")
            def widget(self): ...

        class Compiler(BagCompilerBase):
            pass

        bag = BuilderBag(builder=AttrBuilder)
        bag.widget(color="^theme.color")

        data = Bag()
        data["theme.color"] = "blue"

        compiler = Compiler(bag.builder)
        result = compiler.compile(bag, data=data)

        assert "color=blue" in result


class TestCompileBound:
    """Tests for compile_bound() entry point."""

    def test_compile_bound_skips_preprocess(self):
        """compile_bound goes directly to walk + join."""
        bag = BuilderBag(builder=TagBuilder)
        bag.heading("Direct")

        compiler = TagCompiler(bag.builder)
        result = compiler.compile_bound(bag)

        assert "# Direct" in result
