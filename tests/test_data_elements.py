# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""data_setter and data_formula end-to-end tests.

Covers the user-facing behaviour of data infrastructure elements
(``docs/builders/manager-architecture.md`` §10):

* ``data_setter`` writes a value (or dict-as-Bag) at a path during
  build, and that value is then visible via the data Bag and in any
  ``^pointer`` reference made by other elements.
* ``data_formula`` installs a pull-based resolver: reading the path
  computes the value on demand from its ``^pointer`` dependencies.
* Cascades: a formula that depends on another formula resolves
  transitively.
* Computed attributes: a callable on an element attribute with
  ``^pointer`` defaults is invoked at render time with resolved deps.
* ``_onBuilt``: hook fired after build completes.

Tests assert the user-visible effect (data values, render output),
not internal state.
"""

from __future__ import annotations

import asyncio

from genro_bag import Bag

from tests.helpers import TestBuilder as _Builder


def _maybe_run(result: object) -> None:
    if asyncio.iscoroutine(result):
        asyncio.run(result)


# ---------------------------------------------------------------------------
# data_setter
# ---------------------------------------------------------------------------


class TestDataSetter:
    """``data_setter`` writes values into the builder's local_store."""

    def test_setter_writes_scalar(self) -> None:
        builder = _Builder()
        builder.source.data_setter("title", value="Hello")
        _maybe_run(builder.build())

        assert builder.data["title"] == "Hello"

    def test_setter_value_visible_to_pointer(self) -> None:
        """A pointer rendered after a data_setter sees the written value."""
        builder = _Builder()
        builder.source.data_setter("title", value="From Setter")
        builder.source.heading("^title")
        _maybe_run(builder.build())

        assert "From Setter" in builder.render()

    def test_multiple_setters(self) -> None:
        builder = _Builder()
        builder.source.data_setter("a", value=1)
        builder.source.data_setter("b", value=2)
        _maybe_run(builder.build())

        assert builder.data["a"] == 1
        assert builder.data["b"] == 2

    def test_setter_with_dict_becomes_bag(self) -> None:
        """A dict value is converted to a nested Bag, preserving structure."""
        builder = _Builder()
        builder.source.data_setter(
            "shipping", value={"cost": 25, "days": 3},
        )
        _maybe_run(builder.build())

        nested = builder.data["shipping"]
        assert isinstance(nested, Bag)
        assert nested["cost"] == 25
        assert nested["days"] == 3


# ---------------------------------------------------------------------------
# data_formula — pull model
# ---------------------------------------------------------------------------


class TestDataFormulaPullModel:
    """``data_formula`` installs a pull resolver. Reads recompute on demand."""

    def test_formula_with_static_kwargs(self) -> None:
        builder = _Builder()
        builder.source.data_formula(
            "result", func=lambda a, b: a + b, a=10, b=20,
        )
        _maybe_run(builder.build())

        assert builder.data["result"] == 30

    def test_formula_with_pointer_deps(self) -> None:
        builder = _Builder()
        builder.data["input"] = 5
        builder.source.data_setter("multiplier", value=3)
        builder.source.data_formula(
            "result",
            func=lambda x, m: x * m,
            x="^input",
            m="^multiplier",
        )
        _maybe_run(builder.build())

        assert builder.data["result"] == 15

    def test_formula_returning_dict_becomes_bag(self) -> None:
        builder = _Builder()
        builder.source.data_formula(
            "info",
            func=lambda: {"name": "Alice", "age": 30},
        )
        _maybe_run(builder.build())

        info = builder.data["info"]
        assert isinstance(info, Bag)
        assert info["name"] == "Alice"
        assert info["age"] == 30

    def test_formula_reflects_data_change_on_read(self) -> None:
        """Pull semantics: each read recomputes from the current store."""
        builder = _Builder()
        builder.data["input"] = 10
        builder.source.data_formula(
            "result", func=lambda x: x * 2, x="^input",
        )
        _maybe_run(builder.build())
        assert builder.data["result"] == 20

        builder.data["input"] = 5
        assert builder.data["result"] == 10

    def test_formula_render_reflects_data_change(self) -> None:
        builder = _Builder()
        builder.data["input"] = 10
        builder.source.data_formula(
            "result", func=lambda x: x * 2, x="^input",
        )
        builder.source.heading("^result")
        _maybe_run(builder.build())

        assert "20" in builder.render()
        builder.data["input"] = 5
        assert "10" in builder.render()

    def test_formula_multiple_deps(self) -> None:
        builder = _Builder()
        builder.data["a"] = 3
        builder.data["b"] = 4
        builder.source.data_formula(
            "sum", func=lambda a, b: a + b, a="^a", b="^b",
        )
        _maybe_run(builder.build())

        assert builder.data["sum"] == 7
        builder.data["a"] = 10
        assert builder.data["sum"] == 14
        builder.data["b"] = 1
        assert builder.data["sum"] == 11


# ---------------------------------------------------------------------------
# Cascade: formula depending on another formula
# ---------------------------------------------------------------------------


class TestFormulaCascade:
    """Pull cascade: B depends on A. Reading B triggers A on demand."""

    def test_cascade_resolves_in_order(self) -> None:
        builder = _Builder()
        builder.data["input"] = 10
        builder.source.data_formula(
            "a", func=lambda x: x * 2, x="^input",
        )
        builder.source.data_formula(
            "b", func=lambda x: x + 1, x="^a",
        )
        _maybe_run(builder.build())

        assert builder.data["a"] == 20
        assert builder.data["b"] == 21

    def test_cascade_reactive_to_data_change(self) -> None:
        builder = _Builder()
        builder.data["input"] = 10
        builder.source.data_formula(
            "a", func=lambda x: x * 2, x="^input",
        )
        builder.source.data_formula(
            "b", func=lambda x: x + 1, x="^a",
        )
        _maybe_run(builder.build())

        builder.data["input"] = 5
        assert builder.data["a"] == 10
        assert builder.data["b"] == 11

    def test_independent_formulas_coexist(self) -> None:
        builder = _Builder()
        builder.data["x"] = 1
        builder.data["y"] = 2
        builder.source.data_formula(
            "rx", func=lambda x: x * 10, x="^x",
        )
        builder.source.data_formula(
            "ry", func=lambda y: y * 10, y="^y",
        )
        _maybe_run(builder.build())

        assert builder.data["rx"] == 10
        assert builder.data["ry"] == 20


# ---------------------------------------------------------------------------
# Computed attributes — callable with ^pointer defaults
# ---------------------------------------------------------------------------


class TestComputedAttributes:
    """A callable attribute with ``^pointer`` defaults is invoked at render."""

    def test_callable_attr_resolved_in_render(self) -> None:
        builder = _Builder()
        builder.data["selected"] = True
        builder.source.item(
            color=lambda selected="^selected": "red" if selected else "blue",
        )
        _maybe_run(builder.build())

        assert "red" in builder.render()

    def test_callable_attr_updates_when_data_changes(self) -> None:
        builder = _Builder()
        builder.data["selected"] = True
        builder.source.item(
            color=lambda selected="^selected": "red" if selected else "blue",
        )
        _maybe_run(builder.build())
        assert "red" in builder.render()

        builder.data["selected"] = False
        assert "blue" in builder.render()

    def test_callable_attr_with_multiple_pointer_defaults(self) -> None:
        builder = _Builder()
        builder.data["name"] = "Alice"
        builder.data["role"] = "Admin"
        builder.source.item(
            label=lambda name="^name", role="^role": f"{name} ({role})",
        )
        _maybe_run(builder.build())

        assert "Alice (Admin)" in builder.render()

    def test_plain_callable_uses_its_own_defaults(self) -> None:
        builder = _Builder()
        builder.source.item(value=lambda x=5: x * 2)
        _maybe_run(builder.build())

        assert "10" in builder.render()


# ---------------------------------------------------------------------------
# _onBuilt hook
# ---------------------------------------------------------------------------


class TestOnBuiltHook:
    """``_onBuilt`` fires after build completes for the data element."""

    def test_hook_fires_once_per_build(self) -> None:
        calls: list[object] = []
        builder = _Builder()
        builder.source.data_formula(
            "x", func=lambda: 1,
            _onBuilt=lambda b: calls.append(b),
            _on_built=True,
        )
        _maybe_run(builder.build())

        assert calls == [builder]

    def test_hook_fires_again_on_rebuild(self) -> None:
        calls: list[object] = []
        builder = _Builder()
        builder.source.data_formula(
            "x", func=lambda: 1,
            _onBuilt=lambda b: calls.append("once"),
            _on_built=True,
        )
        _maybe_run(builder.build())
        _maybe_run(builder.build())

        assert calls == ["once", "once"]

    def test_no_hook_means_no_call(self) -> None:
        calls: list[object] = []
        builder = _Builder()
        builder.source.data_setter("k", value=42)
        _maybe_run(builder.build())

        assert calls == []
