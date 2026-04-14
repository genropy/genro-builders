# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for reactivity edge cases — cycles, exceptions, template defaults."""

import inspect

import pytest

from genro_builders import BagBuilderBase
from genro_builders.builder_bag import BuilderBag as Bag
from genro_builders.builder import element
from genro_builders.contrib.html import HtmlBuilder


class TestFormulaChain:
    """Tests for formula dependency chains."""

    def test_long_chain_no_cycle(self):
        """A→B→C→D linear chain (no cycle) works fine."""
        builder = HtmlBuilder()
        s = builder.source
        s.data_setter("input", value=1)
        s.data_formula("a", func=lambda input: input * 2, input="^input")
        s.data_formula("b", func=lambda a: a + 1, a="^a")
        s.data_formula("c", func=lambda b: b * 3, b="^b")
        s.data_formula("d", func=lambda c: c - 1, c="^c")
        body = s.body()
        body.p(value="^d")

        builder.build()
        # input=1, a=2, b=3, c=9, d=8
        assert builder.data["d"] == 8


class TestFormulaExceptions:
    """Tests for formula exception behavior."""

    def test_formula_exception_propagates_during_build(self):
        """Exception in formula during build() propagates to caller."""
        builder = HtmlBuilder()
        s = builder.source
        s.data_setter("x", value=0)
        s.data_formula(
            "result",
            func=lambda x: 1 / x,  # ZeroDivisionError
            x="^x",
        )
        s.body()

        with pytest.raises(ZeroDivisionError):
            builder.build()

    def test_formula_exception_propagates_on_data_change(self):
        """Exception in formula during reactive re-execution propagates."""
        builder = HtmlBuilder()
        s = builder.source
        s.data_setter("x", value=1)
        s.data_formula(
            "result",
            func=lambda x: 1 / x,
            x="^x",
        )
        body = s.body()
        body.p(value="^result")

        builder.build()
        builder.subscribe()

        # Now set x=0 to trigger ZeroDivisionError
        with pytest.raises(ZeroDivisionError):
            builder.data["x"] = 0

    def test_controller_exception_propagates(self):
        """Exception in data_controller propagates during build."""
        builder = HtmlBuilder()
        s = builder.source
        s.data_setter("x", value="not_a_number")

        def bad_controller(x):
            raise ValueError(f"Bad value: {x}")

        s.data_controller(func=bad_controller, x="^x")
        s.body()

        with pytest.raises(ValueError, match="Bad value"):
            builder.build()


class TestTemplateContextDefaults:
    """Tests for template context with parameter defaults."""

    def test_default_values_in_schema(self):
        """Element parameters with defaults are stored in call_args_validations."""

        class ParamBuilder(BagBuilderBase):
            @element()
            def card(self, color: str = "blue", size: int = 3): ...

        builder = ParamBuilder()
        info = builder._get_schema_info("card")
        call_args = info.get("call_args_validations") or {}

        defaults = {}
        for name, (_type, _validators, default) in call_args.items():
            if default is not None and default is not inspect.Parameter.empty:
                defaults[name] = default

        assert defaults["color"] == "blue"
        assert defaults["size"] == 3

    def test_explicit_values_override_defaults(self):
        """Explicitly passed values override defaults in node attributes."""

        class ParamBuilder(BagBuilderBase):
            @element()
            def card(self, color: str = "blue"): ...

        builder = ParamBuilder()
        builder.source.card(node_value="Hello", color="red")
        builder.build()

        node = builder.built.get_node("card_0")
        assert node.attr.get("color") == "red"
