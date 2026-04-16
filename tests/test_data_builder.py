# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for DataBuilder — structured data schemas via builder grammar."""
from __future__ import annotations

from genro_bag import Bag

from genro_builders.builder import component
from genro_builders.contrib.data import DataBuilder
from genro_builders.contrib.html import HtmlBuilder, HtmlManager
from genro_builders.manager import BuilderManager


class TestDataBuilderElement:
    """Tests for the field element."""

    def test_field_creates_source_node(self):
        """field() creates a node in the source."""
        builder = DataBuilder()
        builder.source.field("name", dtype="text", name_long="Full Name")
        assert len(builder.source) == 1

    def test_field_node_has_attrs(self):
        """field node carries dtype and metadata as attributes."""
        builder = DataBuilder()
        node = builder.source.field("name", dtype="text", name_long="Full Name")
        assert node.attr.get("dtype") == "text"
        assert node.attr.get("name_long") == "Full Name"

    def test_field_default_value(self):
        """field node carries default attribute."""
        builder = DataBuilder()
        node = builder.source.field("qty", dtype="integer", default=1)
        assert node.attr.get("default") == 1

    def test_field_format(self):
        """field node carries format attribute."""
        builder = DataBuilder()
        node = builder.source.field("price", dtype="decimal", format="#,##0.00")
        assert node.attr.get("format") == "#,##0.00"

    def test_multiple_fields(self):
        """Multiple fields coexist in source."""
        builder = DataBuilder()
        builder.source.field("name", dtype="text")
        builder.source.field("age", dtype="integer")
        builder.source.field("email", dtype="text")
        assert len(builder.source) == 3


class TestDataBuilderComponent:
    """Tests for component usage in DataBuilder."""

    def test_component_groups_fields(self):
        """A component groups related fields."""

        class AddressData(DataBuilder):
            @component()
            def address(self, comp, **kwargs):
                comp.field("street", dtype="text", name_long="Street")
                comp.field("city", dtype="text", name_long="City")
                comp.field("zip", dtype="text", name_long="ZIP")

        builder = AddressData()
        builder.source.address()
        builder.build()

        addr = builder.built.get_item("address_0")
        assert isinstance(addr, Bag)
        assert len(addr) == 3

    def test_component_inheritance(self):
        """Components are inherited and composable."""

        class BaseData(DataBuilder):
            @component()
            def address(self, comp, **kwargs):
                comp.field("street", dtype="text")
                comp.field("city", dtype="text")

        class CustomerData(BaseData):
            @component()
            def customer(self, comp, **kwargs):
                comp.field("name", dtype="text")
                comp.field("vat", dtype="text")
                comp.address()

        builder = CustomerData()
        builder.source.customer()
        builder.build()

        customer = builder.built.get_item("customer_0")
        assert isinstance(customer, Bag)
        # name + vat + address (expanded to street + city)
        assert len(customer) == 3  # field, field, address_0


class TestOnConfigure:
    """Tests for on_configure() hook."""

    def test_on_configure_called_at_init(self):
        """on_configure() is called during __init__."""
        called = []

        class AutoData(DataBuilder):
            def on_configure(self):
                called.append("configured")
                self.source.field("auto_field", dtype="text")

        builder = AutoData()
        assert called == ["configured"]
        assert len(builder.source) == 1

    def test_on_configure_with_manager(self):
        """on_configure() works when builder is registered via manager."""

        class SchemaData(DataBuilder):
            def on_configure(self):
                self.source.field("name", dtype="text")
                self.source.field("age", dtype="integer")

        class App(BuilderManager):
            def on_init(self):
                self.page = self.register_builder("page", HtmlBuilder)
                self.register_builder("schema", SchemaData)

        app = App()
        schema_builder = app._builders["schema"]
        assert len(schema_builder.source) == 2


class TestDataBuilderIntegration:
    """Integration tests: DataBuilder + HtmlManager."""

    def test_html_manager_has_data_builder(self):
        """HtmlManager registers a DataBuilder named 'data'."""

        class App(HtmlManager):
            def main(self, source):
                source.body()

        app = App()
        assert "data" in app._builders
        assert isinstance(app._builders["data"], DataBuilder)

    def test_data_volume_pointer(self):
        """HTML builder can read data from DataBuilder via ^data:field."""

        class App(HtmlManager):
            def main(self, source):
                self.local_store("data")["company"] = "Acme S.r.l."
                body = source.body()
                body.h1(value="^data:company")

        app = App()
        output = app.render()
        assert "Acme S.r.l." in output

    def test_data_builder_schema_with_html(self):
        """DataBuilder schema + HTML rendering via volume pointer."""

        class InvoiceData(DataBuilder):
            @component()
            def customer(self, comp, **kwargs):
                comp.field("name", dtype="text", name_long="Customer")
                comp.field("vat", dtype="text", name_long="VAT")

            def on_configure(self):
                self.source.customer()

        class InvoiceApp(HtmlManager):
            def on_init(self):
                self.page = self.register_builder("page", HtmlBuilder)
                self.register_builder("invoice", InvoiceData)

            def main(self, source):
                self.local_store("invoice")["customer.name"] = "Acme"
                body = source.body()
                body.h1(value="^invoice:customer.name")

        app = InvoiceApp()
        output = app.render()
        assert "Acme" in output

    def test_local_store_data_namespace(self):
        """local_store('data') writes to the data builder's namespace."""

        class App(HtmlManager):
            def main(self, source):
                self.local_store("data")["year"] = 2026
                body = source.body()
                body.span(value="^data:year")

        app = App()
        output = app.render()
        assert "2026" in output
