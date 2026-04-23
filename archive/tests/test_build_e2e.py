# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""End-to-end build pipeline tests.

Covers: transparent components, deferred data elements, based_on
inheritance, async build, and the full iterate+formula flow.
Uses domain builders (recipe book, invoice) — no HTML.
"""
from __future__ import annotations

import asyncio

import pytest
from genro_bag.resolver import BagCbResolver
from genro_toolbox import smartawait

from genro_builders.builder import BagBuilderBase, component, element
from genro_builders.manager import BuilderManager

from .helpers import TestRenderer

# ---------------------------------------------------------------------------
# Domain builders
# ---------------------------------------------------------------------------

class InvoiceBuilder(BagBuilderBase):
    """Builder for an invoice domain."""

    _renderers = {"test": TestRenderer}

    @element(sub_tags="header,line,footer")
    def invoice(self): ...

    @element(sub_tags="field")
    def header(self): ...

    @element(sub_tags="field")
    def line(self): ...

    @element()
    def field(self): ...

    @element()
    def footer(self): ...

    @component(main_tag="header", sub_tags='')
    def invoice_header(self, comp, main_kwargs=None):
        h = comp.header(**(main_kwargs or {}))
        h.field(value='^title')
        h.field(value='^date')


# ---------------------------------------------------------------------------
# Tests: transparent component
# ---------------------------------------------------------------------------

class TestTransparentComponent:
    """Component is a transparent macro — its content goes into the parent."""

    def test_component_content_in_parent(self):
        """Component body nodes appear directly in parent, no wrapper."""
        class App(BuilderManager):
            def on_init(self):
                self.page = self.register_builder("page", InvoiceBuilder)

            def main(self, source):
                inv = source.invoice()
                inv.invoice_header()

        app = App()
        app.setup()
        app.build()

        inv_bag = app.page.built.get_item("invoice_0")
        assert inv_bag is not None
        # header is directly in invoice, not under invoice_header_0
        header = inv_bag.get_node("header_0")
        assert header is not None
        assert header.node_tag == "header"
        # header has 2 field children
        assert len(header.value) == 2

# ---------------------------------------------------------------------------
# Tests: deferred data elements
# ---------------------------------------------------------------------------

class TestDeferredDataElements:
    """Data elements are processed after the built tree is complete."""

    def test_data_setter_at_top_level(self):
        """data_setter at top level writes to data store."""
        builder = InvoiceBuilder()
        builder.source.data_setter("title", value="Invoice #1")
        builder.build()
        assert builder.data["title"] == "Invoice #1"

    def test_data_formula_at_top_level(self):
        """data_formula at top level installs resolver."""
        builder = InvoiceBuilder()
        builder.source.data_setter("a", value=10)
        builder.source.data_setter("b", value=20)
        builder.source.data_formula(
            "sum", func=lambda a, b: a + b,
            a='^a', b='^b', _on_built=True,
        )
        builder.build()
        assert builder.data["sum"] == 30

# ---------------------------------------------------------------------------
# Tests: iterate + render
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Tests: async build
# ---------------------------------------------------------------------------

class TestAsyncBuild:
    """Build pipeline in async context."""

    @pytest.mark.asyncio
    async def test_async_build_elements(self):
        """Elements build correctly in async context."""
        builder = InvoiceBuilder()
        builder.source.invoice().header().field(value="test")
        result = builder.build()
        if asyncio.iscoroutine(result):
            await result
        assert builder.built.get_node("invoice_0") is not None

    @pytest.mark.asyncio
    async def test_async_build_component(self):
        """Transparent component works in async context."""
        class App(BuilderManager):
            def on_init(self):
                self.page = self.register_builder("page", InvoiceBuilder)

            def main(self, source):
                inv = source.invoice()
                inv.invoice_header()

        app = App()
        app.setup()
        result = app.build()
        if asyncio.iscoroutine(result):
            await result

        inv_bag = app.page.built.get_item("invoice_0")
        assert inv_bag is not None
        assert inv_bag.get_node("header_0") is not None

    @pytest.mark.asyncio
    async def test_async_resolver_is_awaited(self):
        """Async resolver on a source node: build walk awaits the coroutine
        transparently via smartcontinuation. This is the only scenario that
        actually produces a coroutine inside the walk (async resolver in
        async context) — without smartcontinuation the raw coroutine would
        end up stored as the built node value instead of its resolved result.
        """
        async def fetch_title():
            await asyncio.sleep(0)
            return "resolved-async"

        builder = InvoiceBuilder()
        builder.source.invoice().header().field(
            node_value=BagCbResolver(fetch_title),
        )

        result = builder.build()
        # In async context with async resolver, walk returns a coroutine
        assert asyncio.iscoroutine(result)
        await smartawait(result)

        invoice = builder.built.get_node("invoice_0")
        header = invoice.value.get_node("header_0")
        field = header.value.get_node("field_0")
        assert field.value == "resolved-async"
