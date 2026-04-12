# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for component expansion during compile phase.

These tests verify that:
- Component body is called during preprocess/compile (lazy expansion)
- Component receives new Bag with builder
- Component populates the internal bag
- Nested components work correctly
- Builder override works for internal bag
- Component attributes are passed correctly

NOTE: With "Bag Pura" architecture, components are NOT expanded at creation time.
Expansion happens only during compile() via preprocess().
"""

import pytest

from genro_bag import Bag as DataBag
from genro_builders import BagBuilderBase, BagCompilerBase
from genro_builders.binding import BindingManager
from genro_builders.builder_bag import BuilderBag as Bag
from genro_builders.builders import component, element


# =============================================================================
# Simple compiler for testing expansion
# =============================================================================


class TestCompiler(BagCompilerBase):
    """Simple compiler for testing component expansion."""

    def render(self, compiled_bag: Bag) -> str:
        """Render compiled bag to simple string output."""
        return self._render_bag(compiled_bag)

    def _render_bag(self, bag: Bag) -> str:
        """Recursively render bag to string."""
        parts = []
        for node in bag.nodes:
            tag = node.node_tag or node.label
            if isinstance(node.value, Bag):
                children = self._render_bag(node.value)
                parts.append(f"<{tag}>{children}</{tag}>")
            elif node.value:
                parts.append(f"<{tag}>{node.value}</{tag}>")
            else:
                parts.append(f"<{tag}/>")
        return "".join(parts)


def compile_and_render(builder) -> str:
    """Helper: build walk into target, then render to string via TestCompiler."""
    compiler = TestCompiler(builder)
    target = Bag(builder=type(builder))
    builder._build_walk(builder._bag, target, DataBag(), BindingManager())
    return compiler.render(target)


# =============================================================================
# Tests for component expansion
# =============================================================================


class TestComponentExpansion:
    """Tests for component expansion during compile."""

    def test_component_body_called_on_compile(self):
        """Component body is called during compile, not at creation."""
        body_called = False

        class Builder(BagBuilderBase):

            @component()
            def myform(self, comp: Bag, **kwargs):
                nonlocal body_called
                body_called = True
                comp.field()
                return comp

            @element()
            def field(self): ...

        bag = Bag(builder=Builder)
        bag.myform()

        # Body NOT called yet (lazy)
        assert not body_called

        # Now compile - body should be called
        compile_and_render(bag.builder)
        assert body_called

    def test_component_receives_new_bag(self):
        """Component method receives a new Bag with builder during expansion."""
        received_bag = None

        class Builder(BagBuilderBase):

            @component()
            def myform(self, comp: Bag, **kwargs):
                nonlocal received_bag
                received_bag = comp
                return comp

            @element()
            def div(self): ...

        bag = Bag(builder=Builder)
        bag.myform()
        compile_and_render(bag.builder)

        assert received_bag is not None
        assert isinstance(received_bag, Bag)
        # Each Bag gets its own builder instance, but same class
        assert type(received_bag.builder) is type(bag.builder)

    def test_component_populates_bag(self):
        """Component populates the internal bag during expansion."""

        class Builder(BagBuilderBase):

            @component()
            def myform(self, comp: Bag, **kwargs):
                comp.field(name="field1")
                comp.field(name="field2")
                return comp

            @element()
            def field(self): ...

        bag = Bag(builder=Builder)
        bag.myform()

        # Before compile: node exists but value is None or empty
        node = bag.get_node("myform_0")
        assert node is not None
        assert node.node_tag == "myform"

        # Compile triggers expansion
        result = compile_and_render(bag.builder)

        # Output should contain the expanded fields
        assert "<field" in result

    def test_component_uses_builder_elements(self):
        """Component can use builder elements inside during expansion."""

        class Builder(BagBuilderBase):

            @component()
            def myform(self, comp: Bag, **kwargs):
                comp.input(name="field1")
                comp.input(name="field2")
                return comp

            @element()
            def input(self): ...

        bag = Bag(builder=Builder)
        bag.myform()
        result = compile_and_render(bag.builder)

        # Should have input elements in output
        assert "<input" in result


# =============================================================================
# Tests for sub_tags return behavior after expansion
# =============================================================================


class TestComponentSubTagsAfterExpansion:
    """Tests for sub_tags controlling return value after expansion."""

    def test_void_sub_tags_returns_proxy(self):
        """sub_tags='' (void) returns ComponentProxy wrapping parent bag."""
        from genro_builders.component_proxy import ComponentProxy

        class Builder(BagBuilderBase):

            @component(sub_tags="")
            def closed_form(self, comp: Bag, **kwargs):
                comp.internal()
                return comp

            @element()
            def internal(self): ...

            @element()
            def span(self): ...

        bag = Bag(builder=Builder)
        result = bag.closed_form()

        # Returns ComponentProxy wrapping parent bag
        assert isinstance(result, ComponentProxy)
        # Can continue at same level via proxy delegation
        result.span()
        assert len(bag) == 2  # closed_form + span

    def test_component_returns_proxy_for_chaining(self):
        """All components return ComponentProxy wrapping parent bag."""
        from genro_builders.component_proxy import ComponentProxy

        class Builder(BagBuilderBase):

            @component(sub_tags="item")
            def mylist(self, comp: Bag, **kwargs):
                comp.header()
                return comp

            @element()
            def header(self): ...

            @element()
            def item(self): ...

        bag = Bag(builder=Builder)
        result = bag.mylist()

        # All components return proxy
        assert isinstance(result, ComponentProxy)

        # Compile expands the component body
        output = compile_and_render(bag.builder)
        assert "<header" in output


# =============================================================================
# Tests for nested components
# =============================================================================


class TestNestedComponentExpansion:
    """Tests for using components inside components."""

    def test_component_uses_other_component(self):
        """Component can use another component internally."""

        class Builder(BagBuilderBase):

            @component(sub_tags="")
            def inner(self, comp: Bag, **kwargs):
                comp.set_item("inner_data", "value")
                return comp

            @component(sub_tags="")
            def outer(self, comp: Bag, **kwargs):
                comp.inner()  # Use another component
                comp.set_item("outer_data", "value")
                return comp

            @element()
            def div(self): ...

        bag = Bag(builder=Builder)
        bag.outer()

        result = compile_and_render(bag.builder)
        # Should have nested structure
        assert "<outer>" in result
        assert "<inner>" in result

    def test_nested_component_chain(self):
        """Multiple levels of component nesting."""

        class Builder(BagBuilderBase):

            @component(sub_tags="")
            def level3(self, comp: Bag, **kwargs):
                comp.set_item("l3", "data")
                return comp

            @component(sub_tags="")
            def level2(self, comp: Bag, **kwargs):
                comp.level3()
                return comp

            @component(sub_tags="")
            def level1(self, comp: Bag, **kwargs):
                comp.level2()
                return comp

        bag = Bag(builder=Builder)
        bag.level1()

        result = compile_and_render(bag.builder)
        # All levels should be in output
        assert "<level1>" in result
        assert "<level2>" in result
        assert "<level3>" in result


# =============================================================================
# Tests for builder override
# =============================================================================


class TestComponentBuilderOverrideExpansion:
    """Tests for builder override in components during expansion."""

    def test_component_with_different_builder(self):
        """Component can use a different builder for its internal bag."""

        class InnerBuilder(BagBuilderBase):
            @element()
            def special(self): ...

        class OuterBuilder(BagBuilderBase):

            @component(builder=InnerBuilder)
            def with_inner(self, comp: Bag, **kwargs):
                # comp should have InnerBuilder
                comp.special()  # This should work
                return comp

            @element()
            def outer_elem(self): ...

        bag = Bag(builder=OuterBuilder)
        bag.with_inner()

        # Compile expands and uses InnerBuilder internally
        result = compile_and_render(bag.builder)
        assert "<special" in result


# =============================================================================
# Tests for component attributes during expansion
# =============================================================================


class TestComponentAttributesExpansion:
    """Tests for passing attributes to components during expansion."""

    def test_component_receives_kwargs(self):
        """Component receives kwargs passed at call time during expansion."""
        received_kwargs = {}

        class Builder(BagBuilderBase):

            @component(sub_tags="")
            def myform(self, comp: Bag, title=None, **kwargs):
                nonlocal received_kwargs
                received_kwargs = {"title": title, **kwargs}
                return comp

        bag = Bag(builder=Builder)
        bag.myform(title="My Form", extra="data")

        # Compile to trigger expansion
        compile_and_render(bag.builder)

        assert received_kwargs["title"] == "My Form"
        assert received_kwargs["extra"] == "data"

    def test_component_attrs_stored_on_node(self):
        """Component attributes are stored on the node."""

        class Builder(BagBuilderBase):

            @component(sub_tags="")
            def myform(self, comp: Bag, title=None, **kwargs):
                return {"node_value": comp, "title": title, **kwargs}

        bag = Bag(builder=Builder)
        bag.myform(title="Form Title", css_class="my-form")

        # Attributes should be on node even before compile
        node = bag.get_node("myform_0")
        assert node.attr.get("title") == "Form Title"
        assert node.attr.get("css_class") == "my-form"


# =============================================================================
# Tests for component with elements mixed
# =============================================================================


class TestComponentWithElementsExpansion:
    """Tests for mixing components and elements during expansion."""

    def test_component_and_elements_in_same_builder(self):
        """Builder can have both components and elements."""

        class Builder(BagBuilderBase):

            @component(sub_tags="")
            def form(self, comp: Bag, **kwargs):
                comp.input(name="field1")
                return comp

            @element()
            def input(self): ...

            @element()
            def div(self): ...

        bag = Bag(builder=Builder)
        bag.div()
        bag.form()
        bag.div()

        assert len(bag) == 3
        result = compile_and_render(bag.builder)
        assert "<div" in result
        assert "<form>" in result
        assert "<input" in result

    def test_component_inside_element(self):
        """Component can be placed inside an element."""

        class Builder(BagBuilderBase):

            @element(sub_tags="form")
            def div(self): ...

            @component(sub_tags="")
            def form(self, comp: Bag, **kwargs):
                comp.set_item("field", "value")
                return comp

        bag = Bag(builder=Builder)
        div = bag.div()
        div.form()

        result = compile_and_render(bag.builder)
        assert "<div>" in result
        assert "<form>" in result
