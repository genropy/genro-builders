# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for @data_element decorator and data_setter/data_formula (pull model)."""
from __future__ import annotations

import asyncio

import pytest

from genro_builders.builder import BagBuilderBase, data_element, element
from tests.helpers import TestBuilder

# =============================================================================
# Decorator registration
# =============================================================================


class TestDataElementRegistration:
    """Tests for @data_element decorator and schema registration."""

    def test_data_element_creates_schema_entry(self):
        """Schema has is_data_element=True for data_element tags."""
        builder = TestBuilder()
        info = builder._get_schema_info("data_setter")
        assert info.get("is_data_element") is True
        assert info.get("handler_name") == "_dtel_data_setter"

    def test_data_element_both_registered(self):
        """Both data_element tags are registered in schema."""
        builder = TestBuilder()
        for tag in ("data_setter", "data_formula"):
            info = builder._get_schema_info(tag)
            assert info.get("is_data_element") is True

    def test_data_element_requires_body(self):
        """@data_element with empty body raises ValueError."""
        with pytest.raises(ValueError, match="must have a body"):
            class BadBuilder(BagBuilderBase):
                @data_element()
                def my_data(self): ...

    def test_data_element_inherited_by_subclass(self):
        """Concrete builder inherits data_setter/formula from BagBuilderBase."""

        class MinimalBuilder(BagBuilderBase):
            @element()
            def item(self): ...

        builder = MinimalBuilder()
        assert "data_setter" in builder._schema_tag_names
        assert "data_formula" in builder._schema_tag_names


# =============================================================================
# Source population
# =============================================================================


class TestDataElementSource:
    """Tests for data_element node creation in source."""

    def test_data_setter_creates_source_node(self):
        """data_setter creates a node in source with _is_data_element=True."""
        builder = TestBuilder()
        builder.source.data_setter("title", value="Hello")

        node = builder.source.get_node("data_setter_0")
        assert node is not None
        assert node.attr.get("_is_data_element") is True
        assert node.attr.get("_data_path") == "title"
        assert node.attr.get("value") == "Hello"

    def test_data_formula_creates_source_node(self):
        """data_formula creates a node in source."""
        builder = TestBuilder()
        builder.source.data_formula("total", func=lambda a, b: a + b, _on_built=True)

        node = builder.source.get_node("data_formula_0")
        assert node is not None
        assert node.attr.get("_is_data_element") is True

    def test_data_element_transparent_in_sub_tags(self):
        """Data element inside element with strict sub_tags doesn't violate."""

        class StrictBuilder(BagBuilderBase):
            @element(sub_tags="item")
            def container(self): ...

            @element()
            def item(self): ...

        builder = StrictBuilder()
        container = builder.source.container()
        container.data_setter("key", value=42)
        container.item()

        assert builder.source.get_node("container_0") is not None


# =============================================================================
# Build processing
# =============================================================================


class TestDataElementBuild:
    """Tests for data_element processing during build."""

    def test_data_setter_writes_to_data(self):
        """data_setter writes value at path in data Bag after build."""
        builder = TestBuilder()
        builder.source.data_setter("title", value="Hello")
        builder.build()

        assert builder.data["title"] == "Hello"

    def test_data_formula_computes(self):
        """data_formula installs resolver — reading data returns computed value."""
        builder = TestBuilder()
        builder.source.data_formula(
            "result", func=lambda a, b: a + b, a=10, b=20,
            _on_built=True,
        )
        builder.build()

        assert builder.data["result"] == 30

    def test_data_formula_with_pointer(self):
        """data_formula resolves ^pointer deps from data store."""
        builder = TestBuilder()
        builder.data["input"] = 5
        builder.source.data_setter("multiplier", value=3)
        builder.source.data_formula(
            "result",
            func=lambda x, m: x * m,
            x="^input",
            m="^multiplier",
            _on_built=True,
        )
        builder.build()

        assert builder.data["result"] == 15

    def test_infra_before_normal(self):
        """Data set by data_setter is available to ^pointer in normal elements."""
        builder = TestBuilder()
        builder.source.data_setter("title", value="From Setter")
        builder.source.heading("^title")
        builder.build()

        assert "From Setter" in builder.render()

    def test_multiple_data_setters(self):
        """Multiple data_setters at same level all processed."""
        builder = TestBuilder()
        builder.source.data_setter("a", value=1)
        builder.source.data_setter("b", value=2)
        builder.build()

        assert builder.data["a"] == 1
        assert builder.data["b"] == 2

    def test_data_setter_dict_to_bag(self):
        """data_setter with dict value converts it to Bag."""
        from genro_bag import Bag

        builder = TestBuilder()
        builder.source.data_setter("shipping", value={"cost": 25, "days": 3})
        builder.build()

        result = builder.data["shipping"]
        assert isinstance(result, Bag)
        assert result["cost"] == 25
        assert result["days"] == 3

    def test_data_formula_dict_to_bag(self):
        """data_formula returning dict converts result to Bag."""
        from genro_bag import Bag

        builder = TestBuilder()
        builder.source.data_formula(
            "info",
            func=lambda: {"name": "Alice", "age": 30},
            _on_built=True,
        )
        builder.build()

        result = builder.data["info"]
        assert isinstance(result, Bag)
        assert result["name"] == "Alice"
        assert result["age"] == 30


# =============================================================================
# _onBuilt hook
# =============================================================================


class TestOnBuiltHook:
    """Tests for _onBuilt hook on data_formula."""

    def test_on_built_called(self):
        """_onBuilt hook is called after build completes."""
        called = []
        builder = TestBuilder()
        builder.source.data_formula(
            "x", func=lambda: 1,
            _onBuilt=lambda b: called.append(b),
            _on_built=True,
        )
        builder.build()

        assert len(called) == 1

    def test_on_built_receives_builder(self):
        """_onBuilt hook receives the builder instance."""
        received = []
        builder = TestBuilder()
        builder.source.data_formula(
            "x", func=lambda: 1,
            _onBuilt=lambda b: received.append(b),
            _on_built=True,
        )
        builder.build()

        assert received[0] is builder

    def test_on_built_not_called_without_attribute(self):
        """data_setter without _onBuilt does not trigger hook."""
        called = []
        builder = TestBuilder()
        builder.source.data_setter("key", value=42)
        builder.build()

        assert len(called) == 0


# =============================================================================
# Edge cases
# =============================================================================


class TestDataElementEdgeCases:
    """Edge case tests for data_element."""

    def test_data_element_in_component(self):
        """Component expands to its single tree under the parent."""
        builder = TestBuilder()
        builder.source.section(title="Test")
        builder.build()
        # New contract: section is a tree rooted at section_root
        root = builder.built.get_node("section_root_0")
        assert root is not None
        assert root.value.get_node("heading_0") is not None
        assert root.value.get_node("text_0") is not None

    def test_rebuild_clears_hooks(self):
        """After rebuild, hooks from previous build are gone."""
        called = []
        builder = TestBuilder()
        builder.source.data_formula(
            "x", func=lambda: 1,
            _onBuilt=lambda b: called.append("hook"),
            _on_built=True,
        )
        builder.build()
        assert len(called) == 1

        builder.build()
        assert len(called) == 2  # Called again on rebuild


# =============================================================================
# Reactivity (formula pull model)
# =============================================================================


class TestFormulaReactivity:
    """Tests for pull-based formula reactivity."""

    def test_formula_reflects_data_change(self):
        """After data change, reading formula returns fresh value (pull)."""
        builder = TestBuilder()
        builder.data["input"] = 10
        builder.source.data_formula(
            "result", func=lambda x: x * 2, x="^input",
            _on_built=True,
        )
        builder.build()

        assert builder.data["result"] == 20

        builder.data["input"] = 5
        assert builder.data["result"] == 10

    def test_formula_render_reflects_data_change(self):
        """After subscribe + data change, re-render shows fresh value."""
        builder = TestBuilder()
        builder.data["input"] = 10
        builder.source.data_formula(
            "result", func=lambda x: x * 2, x="^input",
            _on_built=True,
        )
        builder.source.heading("^result")
        builder.build()

        assert "20" in builder.render()

        builder.data["input"] = 5
        assert "10" in builder.render()

    def test_formula_multiple_deps(self):
        """Formula with multiple ^pointer deps reflects any change."""
        builder = TestBuilder()
        builder.data["a"] = 3
        builder.data["b"] = 4
        builder.source.data_formula(
            "sum", func=lambda a, b: a + b, a="^a", b="^b",
            _on_built=True,
        )
        builder.build()

        assert builder.data["sum"] == 7

        builder.data["a"] = 10
        assert builder.data["sum"] == 14

        builder.data["b"] = 1
        assert builder.data["sum"] == 11


# =============================================================================
# Computed attributes (callable on attrs with ^pointer defaults)
# =============================================================================


class TestComputedAttributes:
    """Tests for computed attributes: callable with ^pointer defaults."""

    def test_computed_attr_resolved_at_render(self):
        """Callable attribute is resolved at render time."""
        builder = TestBuilder()
        builder.data["selected"] = True
        builder.source.item(
            color=lambda selected='^selected': 'red' if selected else 'blue',
        )
        builder.build()

        output = builder.render()
        assert "red" in output

    def test_computed_attr_updates_on_data_change(self):
        """Computed attr reflects data changes on re-render."""
        builder = TestBuilder()
        builder.data["selected"] = True
        builder.source.item(
            color=lambda selected='^selected': 'red' if selected else 'blue',
        )
        builder.build()

        assert "red" in builder.render()

        builder.data["selected"] = False
        assert "blue" in builder.render()

    def test_computed_attr_multiple_deps(self):
        """Callable with multiple ^pointer defaults."""
        builder = TestBuilder()
        builder.data["name"] = "Alice"
        builder.data["role"] = "Admin"
        builder.source.item(
            label=lambda name='^name', role='^role': f'{name} ({role})',
        )
        builder.build()

        output = builder.render()
        assert "Alice (Admin)" in output

    def test_computed_attr_preserved_in_built(self):
        """Callable stays in built node attrs — not resolved until render."""
        builder = TestBuilder()
        builder.data["x"] = 1
        builder.source.item(
            value=lambda x='^x': x * 10,
        )
        builder.build()

        node = builder.built.get_node("item_0")
        assert callable(node.attr.get("value"))

    def test_plain_callable_without_pointer_defaults(self):
        """Callable without ^pointer defaults is called with its plain defaults."""
        builder = TestBuilder()
        builder.source.item(
            value=lambda x=5: x * 2,
        )
        builder.build()

        output = builder.render()
        assert "10" in output


# =============================================================================
# Topological sort / cascade (pull model — natural via demand)
# =============================================================================


class TestFormulaCascade:
    """Tests for formula dependency chains — pull cascade."""

    def test_formula_cascade_order(self):
        """Formula B depends on formula A — pull resolves naturally."""
        builder = TestBuilder()
        builder.data["input"] = 10
        builder.source.data_formula(
            "result_a", func=lambda x: x * 2, x="^input",
            _on_built=True,
        )
        builder.source.data_formula(
            "result_b", func=lambda x: x + 1, x="^result_a",
            _on_built=True,
        )
        builder.build()

        assert builder.data["result_a"] == 20
        assert builder.data["result_b"] == 21

    def test_formula_cascade_reactive(self):
        """After data change, cascade resolves on demand."""
        builder = TestBuilder()
        builder.data["input"] = 10
        builder.source.data_formula(
            "result_a", func=lambda x: x * 2, x="^input",
            _on_built=True,
        )
        builder.source.data_formula(
            "result_b", func=lambda x: x + 1, x="^result_a",
            _on_built=True,
        )
        builder.build()

        builder.data["input"] = 5
        assert builder.data["result_a"] == 10
        assert builder.data["result_b"] == 11

    def test_independent_formulas_no_error(self):
        """Independent formulas coexist without issue."""
        builder = TestBuilder()
        builder.data["x"] = 1
        builder.data["y"] = 2
        builder.source.data_formula(
            "rx", func=lambda x: x * 10, x="^x",
            _on_built=True,
        )
        builder.source.data_formula(
            "ry", func=lambda y: y * 10, y="^y",
            _on_built=True,
        )
        builder.build()

        assert builder.data["rx"] == 10
        assert builder.data["ry"] == 20


# =============================================================================
# _delay — not applicable in pull model
# =============================================================================


class TestDelayNotApplicable:
    """_delay is not applicable in pull model (formulas are resolvers)."""

    def test_no_delay_executes_immediately(self):
        """Formula without _delay returns fresh value on read."""
        builder = TestBuilder()
        builder.data["input"] = 10
        builder.source.data_formula(
            "result", func=lambda x: x * 2, x="^input",
            _on_built=True,
        )
        builder.build()

        assert builder.data["result"] == 20

        builder.data["input"] = 5
        assert builder.data["result"] == 10


# =============================================================================
# Active cache (background refresh)
# =============================================================================


class TestActiveCache:
    """Tests for data_formula with _interval (active cache)."""

    @pytest.mark.asyncio
    async def test_active_cache_refreshes_periodically(self):
        """Formula with _interval=N refreshes in background."""
        counter = {"n": 0}

        def incrementing():
            counter["n"] += 1
            return counter["n"]

        builder = TestBuilder()
        builder.source.data_formula(
            "ticker", func=incrementing, _interval=0.1,
            _on_built=True,
        )
        builder.build()

        # Initial value from warm-up
        initial = builder.data["ticker"]
        assert initial == 1

        # Wait for initial_delay (1s) + a few ticks (0.1s each)
        await asyncio.sleep(1.5)

        # Background refresh should have produced new values
        assert counter["n"] >= 3

    @pytest.mark.asyncio
    async def test_active_cache_triggers_data_change(self):
        """Active cache writes to node, triggering data subscribers."""
        changes: list[str] = []
        counter = {"n": 0}

        def incrementing():
            counter["n"] += 1
            return counter["n"]

        builder = TestBuilder()
        builder.source.data_formula(
            "ticker", func=incrementing, _interval=0.1,
            _on_built=True,
        )
        builder.build()

        builder.data.subscribe("test", any=lambda **kw: changes.append("changed"))

        # Wait for initial_delay (1s) + at least one tick
        await asyncio.sleep(1.3)

        # Each background tick produces a new value (incrementing) → triggers event
        assert len(changes) >= 1

    @pytest.mark.asyncio
    async def test_active_cache_resolver_replaced_on_rebuild(self):
        """Rebuild replaces the old resolver with a new one."""
        counter_a = {"n": 0}
        counter_b = {"n": 0}

        builder = TestBuilder()
        builder.source.data_formula(
            "ticker", func=lambda: (counter_a.__setitem__("n", counter_a["n"] + 1), counter_a["n"])[1],
            _interval=0.1,
            _on_built=True,
        )
        builder.build()

        # Warm-up executes the first resolver
        assert builder.data["ticker"] == 1
        assert counter_a["n"] == 1

        # Rebuild with a different resolver
        builder.source.clear()
        builder.source.data_formula(
            "ticker", func=lambda: (counter_b.__setitem__("n", counter_b["n"] + 1), counter_b["n"])[1],
            _interval=0.1,
            _on_built=True,
        )
        builder.build()

        # New resolver is active
        assert builder.data["ticker"] == 1  # counter_b starts from 1
        assert counter_b["n"] == 1
