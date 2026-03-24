# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for ComponentResolver — lazy expansion via BagResolver."""
from __future__ import annotations

from genro_builders import BagBuilderBase, BagCompilerBase, ComponentResolver
from genro_builders.builder_bag import BuilderBag as Bag
from genro_builders.builders import component, element
from genro_builders.compiler import compile_handler


class SimpleCompiler(BagCompilerBase):
    """Compiler for testing — renders tags as <tag>children</tag>."""

    def render(self, compiled_bag):
        return self._render_bag(compiled_bag)

    def _render_bag(self, bag):
        parts = []
        for node in bag:
            tag = node.node_tag or node.label
            if isinstance(node.value, Bag):
                children = self._render_bag(node.value)
                parts.append(f"<{tag}>{children}</{tag}>")
            elif node.value:
                parts.append(f"<{tag}>{node.value}</{tag}>")
            else:
                parts.append(f"<{tag}/>")
        return "".join(parts)


class TestResolverCreation:
    """Tests that ComponentResolver is set on component nodes."""

    def test_component_node_has_resolver(self):
        """Component node gets a ComponentResolver attached."""

        class B(BagBuilderBase):
            @component()
            def myform(self, comp, **kwargs):
                return comp

        bag = Bag(builder=B)
        bag.myform()

        node = bag.get_node("myform_0")
        assert node.resolver is not None
        assert isinstance(node.resolver, ComponentResolver)

    def test_handler_not_called_at_creation(self):
        """Component handler body is NOT called when the component is created."""
        called = False

        class B(BagBuilderBase):
            @component()
            def myform(self, comp, **kwargs):
                nonlocal called
                called = True
                return comp

        bag = Bag(builder=B)
        bag.myform()

        assert not called

    def test_handler_called_on_resolve(self):
        """Handler is called when resolver is triggered (static=False)."""
        called = False

        class B(BagBuilderBase):
            @component()
            def myform(self, comp, **kwargs):
                nonlocal called
                called = True
                return comp

        bag = Bag(builder=B)
        bag.myform()

        node = bag.get_node("myform_0")
        node.get_value(static=False)

        assert called

    def test_component_returns_parent_bag(self):
        """All components return parent bag for chaining."""

        class B(BagBuilderBase):
            @component()
            def myform(self, comp, **kwargs):
                return comp

        bag = Bag(builder=B)
        result = bag.myform()
        assert result is bag


class TestResolverExpansion:
    """Tests for ComponentResolver.load() producing expanded Bag."""

    def test_load_returns_populated_bag(self):
        """Resolver load() returns a Bag populated by the handler."""

        class B(BagBuilderBase):
            @element()
            def field(self): ...

            @component()
            def myform(self, comp, **kwargs):
                comp.field(name="f1")
                comp.field(name="f2")

        bag = Bag(builder=B)
        bag.myform()

        node = bag.get_node("myform_0")
        expanded = node.get_value(static=False)

        assert isinstance(expanded, Bag)
        assert len(expanded) == 2

    def test_kwargs_passed_to_handler(self):
        """Node attributes are passed as kwargs to the handler."""
        received = {}

        class B(BagBuilderBase):
            @component()
            def myform(self, comp, title=None, **kwargs):
                nonlocal received
                received = {"title": title, **kwargs}

        bag = Bag(builder=B)
        bag.myform(title="Hello", extra="data")

        node = bag.get_node("myform_0")
        node.get_value(static=False)

        assert received["title"] == "Hello"
        assert received["extra"] == "data"

    def test_nested_components_have_resolvers(self):
        """Components inside components also get resolvers."""

        class B(BagBuilderBase):
            @element()
            def leaf(self): ...

            @component()
            def inner(self, comp, **kwargs):
                comp.leaf()

            @component()
            def outer(self, comp, **kwargs):
                comp.inner()

        bag = Bag(builder=B)
        bag.outer()

        node = bag.get_node("outer_0")
        expanded = node.get_value(static=False)

        # The expanded bag should contain inner_0 with its own resolver
        inner_node = expanded.get_node("inner_0")
        assert inner_node is not None
        assert inner_node.resolver is not None

    def test_read_only_preserves_node_value(self):
        """read_only=True: resolver does not overwrite node._value."""

        class B(BagBuilderBase):
            @element()
            def field(self): ...

            @component()
            def myform(self, comp, **kwargs):
                comp.field(name="f1")

        bag = Bag(builder=B)
        bag.myform()

        node = bag.get_node("myform_0")
        assert node.static_value is None

        # Trigger resolver
        node.get_value(static=False)

        # _value should still be None (read_only=True)
        assert node.static_value is None


class TestBasedOn:
    """Tests for component inheritance via based_on."""

    def test_based_on_simple(self):
        """Derived component gets content from base + its own additions."""

        class B(BagBuilderBase):
            @element()
            def item(self): ...

            @component()
            def base_list(self, comp, **kwargs):
                comp.item("item1")
                comp.item("item2")

            @component(based_on="base_list")
            def extended_list(self, comp, **kwargs):
                comp.item("item3")

        bag = Bag(builder=B)
        bag.extended_list()

        node = bag.get_node("extended_list_0")
        expanded = node.get_value(static=False)

        assert len(expanded) == 3
        values = [n.value for n in expanded]
        assert "item1" in values
        assert "item2" in values
        assert "item3" in values

    def test_based_on_chain(self):
        """Three-level inheritance chain: A -> B -> C."""

        class B(BagBuilderBase):
            @element()
            def item(self): ...

            @component()
            def level1(self, comp, **kwargs):
                comp.item("from_level1")

            @component(based_on="level1")
            def level2(self, comp, **kwargs):
                comp.item("from_level2")

            @component(based_on="level2")
            def level3(self, comp, **kwargs):
                comp.item("from_level3")

        bag = Bag(builder=B)
        bag.level3()

        node = bag.get_node("level3_0")
        expanded = node.get_value(static=False)

        values = [n.value for n in expanded]
        assert "from_level1" in values
        assert "from_level2" in values
        assert "from_level3" in values

    def test_based_on_with_compile(self):
        """based_on works through the full compile pipeline."""

        class B(BagBuilderBase):
            _compiler_class = SimpleCompiler

            @element()
            def field(self): ...

            @component()
            def base_form(self, comp, **kwargs):
                comp.field(name="name")

            @component(based_on="base_form")
            def extended_form(self, comp, **kwargs):
                comp.field(name="email")

        bag = Bag(builder=B)
        bag.extended_form()

        compiled = bag.builder._compile()
        result = bag.builder._compiler.render(compiled)
        assert "<field" in result  # Should have fields from both base and extended

    def test_based_on_with_expand(self):
        """based_on works with the expander."""
        from genro_builders.expander import expand

        class B(BagBuilderBase):
            @element()
            def item(self): ...

            @component()
            def base(self, comp, **kwargs):
                comp.item("base_item")

            @component(based_on="base")
            def derived(self, comp, **kwargs):
                comp.item("derived_item")

        bag = Bag(builder=B)
        bag.derived()

        expanded = list(expand(bag))
        values = [node.value for _, node in expanded]
        assert "base_item" in values
        assert "derived_item" in values


class TestBuilderOverride:
    """Tests for component_builder (builder= parameter on @component)."""

    def test_component_uses_different_builder(self):
        """Component with builder= uses that builder for internal bag."""

        class InnerBuilder(BagBuilderBase):
            @element()
            def special(self): ...

        class OuterBuilder(BagBuilderBase):
            _compiler_class = SimpleCompiler

            @component(builder=InnerBuilder)
            def with_inner(self, comp, **kwargs):
                comp.special()

            @element()
            def normal(self): ...

        bag = Bag(builder=OuterBuilder)
        bag.with_inner()

        compiled = bag.builder._compile()
        result = bag.builder._compiler.render(compiled)
        assert "<special" in result
