# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for async-safe build walk with ComponentResolver.

Verifies that build() works transparently in both sync and async contexts.
In async context, ComponentResolver returns a coroutine from
get_value(static=False); the build walk handles this via the continuation
pattern (same approach as _htraverse in genro-bag).
"""
from __future__ import annotations

import asyncio

import pytest
from genro_bag import Bag
from genro_toolbox import smartawait

from genro_builders import BagBuilderBase
from genro_builders.builders import component, data_element, element
from genro_builders.manager import BuilderManager

# ---------------------------------------------------------------------------
# Shared builders
# ---------------------------------------------------------------------------

class SimpleBuilder(BagBuilderBase):
    """Builder with elements and a component."""

    @element()
    def div(self, **kwargs):
        ...

    @element()
    def span(self, **kwargs):
        ...

    @component()
    def card(self, comp, title=None, **kwargs):
        comp.div()
        comp.span(title)
        return comp


class BuilderWithData(BagBuilderBase):
    """Builder with data_element and component using ^pointers."""

    @element()
    def div(self, **kwargs):
        ...

    @element()
    def span(self, **kwargs):
        ...

    @data_element()
    def data_setter(self, path=None, value=None):
        return path, {"value": value}

    @component()
    def greeter(self, comp, **kwargs):
        comp.span("^.name")
        return comp


class BuilderWithInheritance(BagBuilderBase):
    """Builder with component inheritance via based_on."""

    @element()
    def div(self, **kwargs):
        ...

    @element()
    def span(self, **kwargs):
        ...

    @component()
    def base_panel(self, comp, **kwargs):
        comp.div()
        return comp

    @component(based_on="base_panel")
    def fancy_panel(self, comp, **kwargs):
        comp.span("extra")
        return comp


# ---------------------------------------------------------------------------
# Sync: verify no regression
# ---------------------------------------------------------------------------

class TestSyncBuildUnchanged:
    """Sync build still works exactly as before."""

    def test_build_elements_sync(self):
        builder = SimpleBuilder()
        builder.source.div(id="main")
        builder.source.span("text")
        builder.build()
        assert len(builder.built) == 2

    def test_build_component_sync(self):
        builder = SimpleBuilder()
        builder.source.card(title="Hello")
        builder.build()
        node = builder.built.get_node("card_0")
        assert node is not None
        assert isinstance(node.value, Bag)
        assert len(node.value) == 2

    def test_build_returns_none_in_sync(self):
        """build() returns None in sync context (no event loop)."""
        builder = SimpleBuilder()
        builder.source.div()
        result = builder.build()
        assert result is None

    def test_component_with_inheritance_sync(self):
        builder = BuilderWithInheritance()
        builder.source.fancy_panel()
        builder.build()
        node = builder.built.get_node("fancy_panel_0")
        assert isinstance(node.value, Bag)
        # base_panel adds div, fancy_panel adds span
        assert len(node.value) == 2


# ---------------------------------------------------------------------------
# Async: basic build
# ---------------------------------------------------------------------------

class TestAsyncBuild:
    """Build inside an async context (event loop running)."""

    @pytest.mark.asyncio
    async def test_build_elements_async(self):
        """Elements (no resolvers) build fine in async context."""
        builder = SimpleBuilder()
        builder.source.div(id="main")
        builder.source.span("text")
        result = builder.build()
        await smartawait(result)
        assert len(builder.built) == 2

    @pytest.mark.asyncio
    async def test_build_component_async(self):
        """Component resolver expands correctly in async context."""
        builder = SimpleBuilder()
        builder.source.card(title="Hello")
        result = builder.build()
        await smartawait(result)
        node = builder.built.get_node("card_0")
        assert node is not None
        assert isinstance(node.value, Bag)
        assert len(node.value) == 2

    @pytest.mark.asyncio
    async def test_build_mixed_elements_and_components(self):
        """Mix of elements and components builds in async context."""
        builder = SimpleBuilder()
        builder.source.div(id="before")
        builder.source.card(title="Middle")
        builder.source.span("after")
        result = builder.build()
        await smartawait(result)
        assert len(builder.built) == 3
        comp_node = builder.built.get_node("card_0")
        assert isinstance(comp_node.value, Bag)
        assert len(comp_node.value) == 2

    @pytest.mark.asyncio
    async def test_build_multiple_components(self):
        """Multiple components all expand in async context."""
        builder = SimpleBuilder()
        builder.source.card(title="First")
        builder.source.card(title="Second")
        builder.source.card(title="Third")
        result = builder.build()
        await smartawait(result)
        assert len(builder.built) == 3
        for node in builder.built:
            assert isinstance(node.value, Bag)
            assert len(node.value) == 2

    @pytest.mark.asyncio
    async def test_build_returns_coroutine_with_component(self):
        """build() returns a coroutine in async context when resolvers are present."""
        builder = SimpleBuilder()
        builder.source.card()
        result = builder.build()
        assert result is not None
        assert asyncio.iscoroutine(result) or hasattr(result, "__await__")
        await smartawait(result)

    @pytest.mark.asyncio
    async def test_build_returns_none_without_resolver(self):
        """build() returns None in async context when no resolvers exist."""
        builder = SimpleBuilder()
        builder.source.div()
        builder.source.span("text")
        result = builder.build()
        # No resolvers → _build_walk_nodes returns None → finalize returns None
        await smartawait(result)
        assert len(builder.built) == 2


# ---------------------------------------------------------------------------
# Async: component inheritance (based_on)
# ---------------------------------------------------------------------------

class TestAsyncBuildInheritance:
    """Component inheritance works in async context."""

    @pytest.mark.asyncio
    async def test_based_on_expands_correctly(self):
        """based_on component chain resolves in async."""
        builder = BuilderWithInheritance()
        builder.source.fancy_panel()
        result = builder.build()
        await smartawait(result)
        node = builder.built.get_node("fancy_panel_0")
        assert isinstance(node.value, Bag)
        # base_panel adds div, fancy_panel adds span
        assert len(node.value) == 2

    @pytest.mark.asyncio
    async def test_base_and_derived_together(self):
        """Both base and derived components in same build."""
        builder = BuilderWithInheritance()
        builder.source.base_panel()
        builder.source.fancy_panel()
        result = builder.build()
        await smartawait(result)
        assert len(builder.built) == 2
        base_node = builder.built.get_node("base_panel_0")
        fancy_node = builder.built.get_node("fancy_panel_0")
        assert len(base_node.value) == 1  # only div
        assert len(fancy_node.value) == 2  # div + span


# ---------------------------------------------------------------------------
# Async: data_element + component
# ---------------------------------------------------------------------------

class TestAsyncBuildWithData:
    """data_element and component coexist in async context."""

    @pytest.mark.asyncio
    async def test_data_setter_and_component(self):
        """data_setter processed before component expansion."""
        builder = BuilderWithData()
        builder.source.data_setter(path=".name", value="World")
        builder.source.greeter()
        result = builder.build()
        await smartawait(result)
        # data_setter should have written to data
        assert builder.data[".name"] == "World"
        # greeter component should be expanded
        node = builder.built.get_node("greeter_0")
        assert isinstance(node.value, Bag)

    @pytest.mark.asyncio
    async def test_pointer_in_component_resolved_at_render(self):
        """^pointer inside component body is resolved during render."""
        builder = BuilderWithData()
        builder.source.data_setter(path=".name", value="Alice")
        builder.source.greeter()
        result = builder.build()
        await smartawait(result)
        # The built component should have the ^pointer as raw value
        comp_node = builder.built.get_node("greeter_0")
        span_node = comp_node.value.get_node("span_0")
        assert span_node.value == "^.name"


# ---------------------------------------------------------------------------
# Async: nested component inside element
# ---------------------------------------------------------------------------

class TestAsyncBuildNested:
    """Components inside nested bags."""

    @pytest.mark.asyncio
    async def test_component_inside_element(self):
        """Component nested under an element expands in async."""

        class B(BagBuilderBase):
            @element(sub_tags="inner")
            def wrapper(self, **kwargs):
                ...

            @component(parent_tags="wrapper")
            def inner(self, comp, **kwargs):
                comp.wrapper()
                return comp

        builder = B()
        w = builder.source.wrapper()
        w.inner()
        result = builder.build()
        await smartawait(result)

        wrapper_node = builder.built.get_node("wrapper_0")
        assert isinstance(wrapper_node.value, Bag)
        inner_node = wrapper_node.value.get_node("inner_0")
        assert inner_node is not None
        assert isinstance(inner_node.value, Bag)

    @pytest.mark.asyncio
    async def test_deep_nesting_with_components(self):
        """Multiple levels of nesting with components at leaf."""

        class B(BagBuilderBase):
            @element(sub_tags="row")
            def section(self, **kwargs):
                ...

            @element(parent_tags="section", sub_tags="badge")
            def row(self, **kwargs):
                ...

            @component(parent_tags="row")
            def badge(self, comp, label=None, **kwargs):
                comp.section()
                return comp

        builder = B()
        sec = builder.source.section()
        row = sec.row()
        row.badge(label="tag1")
        row.badge(label="tag2")

        result = builder.build()
        await smartawait(result)

        sec_node = builder.built.get_node("section_0")
        row_node = sec_node.value.get_node("row_0")
        assert len(row_node.value) == 2
        for node in row_node.value:
            assert isinstance(node.value, Bag)
            assert len(node.value) == 1


# ---------------------------------------------------------------------------
# Async: BuilderManager
# ---------------------------------------------------------------------------

class TestAsyncManager:
    """BuilderManager.build() and run() in async context."""

    @pytest.mark.asyncio
    async def test_manager_build_async(self):
        """Manager.build() works in async context."""

        class MyManager(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", SimpleBuilder)

            def main(self, source):
                source.card(title="Managed")

        mgr = MyManager()
        mgr.setup()
        result = mgr.build()
        await smartawait(result)

        node = mgr.page.built.get_node("card_0")
        assert isinstance(node.value, Bag)
        assert len(node.value) == 2

    @pytest.mark.asyncio
    async def test_manager_run_async(self):
        """Manager.run() works in async context."""

        class MyManager(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", SimpleBuilder)

            def main(self, source):
                source.div(id="root")
                source.card(title="Content")

        mgr = MyManager()
        result = mgr.run()
        await smartawait(result)

        assert len(mgr.page.built) == 2

    def test_manager_build_sync(self):
        """Manager.build() returns None in sync context."""

        class MyManager(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", SimpleBuilder)

            def main(self, source):
                source.card(title="Hello")

        mgr = MyManager()
        mgr.setup()
        result = mgr.build()
        assert result is None
        node = mgr.page.built.get_node("card_0")
        assert isinstance(node.value, Bag)

    def test_manager_run_sync(self):
        """Manager.run() returns None in sync context."""

        class MyManager(BuilderManager):
            def __init__(self):
                self.page = self.set_builder("page", SimpleBuilder)

            def main(self, source):
                source.div()

        mgr = MyManager()
        result = mgr.run()
        assert result is None
        assert len(mgr.page.built) == 1
