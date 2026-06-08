# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests per il decoratore @struct_method.

Comportamento legacy (gnrwebstruct/base.py:40-92):
- firma: def widget(self, pane, *args, **kwargs)
- naming automatico: se il nome del metodo contiene "_", il prefisso prima
  del primo "_" viene rimosso (iv_widget -> widget)
- naming esplicito: @struct_method('nome')
- collisione: errore se due metodi con func.__name__ diverso registrano
  lo stesso nome di dispatch (subclass che ridichiara con stesso
  func.__name__ è OK = override Python normale)
- dispatch case-insensitive (sotto-step 1)
"""
from __future__ import annotations

import inspect

import pytest

from genro_builders import struct_method
from genro_builders.contrib.html import HtmlBuilder
from genro_builders.contrib.svg import SvgBuilder

# --- Sotto-step 2: metadata ---------------------------------------------------

def test_struct_method_marks_function():
    @struct_method
    def block(self, pane, x):
        pane.div(value=x)

    assert hasattr(block, "_decorator")
    assert block._decorator.get("struct_method") is True


def test_struct_method_requires_body():
    with pytest.raises(ValueError, match="must have a body"):
        @struct_method
        def empty(self, pane): ...


def test_struct_method_preserves_signature():
    @struct_method
    def block(self, pane, x, y=1, **kw):
        pane.div(x=x, y=y)

    sig = inspect.signature(block)
    params = list(sig.parameters.keys())
    assert params == ["self", "pane", "x", "y", "kw"]


def test_struct_method_importable_top_level():
    from genro_builders import struct_method as sm
    assert sm is struct_method


# --- Sotto-step 3: dispatch ---------------------------------------------------

def test_struct_method_invoked_via_node():
    class P(HtmlBuilder):
        @struct_method
        def block(self, pane):
            pane.h1("ok")

        def main(self, root):
            pass

    page = P()
    page.create()
    page.source.body().block()
    assert "<h1>ok</h1>" in page.render()


def test_struct_method_receives_builder_as_self_and_node_as_pane():
    received = {}

    class P(HtmlBuilder):
        @struct_method
        def record(self, pane):
            received["self"] = self
            received["pane"] = pane

        def main(self, root):
            pass

    page = P()
    page.create()
    body = page.source.body()
    body.record()
    assert received["self"] is page
    assert received["pane"] is body


def test_struct_method_args_kwargs_forwarded():
    class P(HtmlBuilder):
        @struct_method
        def card(self, pane, title, color="blue"):
            pane.div(class_=f"card {color}").h2(title)

        def main(self, root):
            pass

    page = P()
    page.create()
    page.source.body().card("Hello", color="red")
    out = page.render()
    assert 'class="card red"' in out
    assert "<h2>Hello</h2>" in out


def test_struct_method_case_insensitive():
    class P(HtmlBuilder):
        @struct_method
        def my_block(self, pane):
            pane.span("ok")

        def main(self, root):
            pass

    page = P()
    page.create()
    # my_block ha "_", quindi il nome di registrazione è "block".
    # Verifico sia case-insensitive sul nome registrato.
    page.source.body().BLOCK()
    assert "<span>ok</span>" in page.render()


def test_struct_method_prefix_strip():
    """def iv_widget(self, pane) -> registrato come 'widget' (legacy)."""

    class P(HtmlBuilder):
        @struct_method
        def iv_widget(self, pane):
            pane.span("stripped")

        def main(self, root):
            pass

    page = P()
    page.create()
    page.source.body().widget()
    assert "stripped" in page.render()


def test_struct_method_explicit_name():
    """@struct_method('alias') sovrascrive il naming automatico."""

    class P(HtmlBuilder):
        @struct_method('alias')
        def some_internal_name(self, pane):
            pane.span("aliased")

        def main(self, root):
            pass

    page = P()
    page.create()
    page.source.body().alias()
    assert "aliased" in page.render()


def test_struct_method_collision_different_funcs_raises():
    """Due funzioni con __name__ diverso che registrano lo stesso nome
    di dispatch → ValueError (legacy)."""
    with pytest.raises(ValueError, match="(?i)already tied|already registered|duplicate"):

        class _Bad(HtmlBuilder):
            @struct_method('widget')
            def first_impl(self, pane):
                pane.div()

            @struct_method('widget')
            def second_impl(self, pane):
                pane.div()

            def main(self, root):
                pass


def test_struct_method_subclass_override_same_name_is_ok():
    """Una subclass che ridichiara @struct_method con stesso func.__name__
    del parent → override Python normale, NO errore (legacy idempotente)."""

    class A(HtmlBuilder):
        @struct_method
        def widget(self, pane):
            pane.span("parent")

        def main(self, root):
            pass

    class B(A):
        @struct_method
        def widget(self, pane):
            pane.span("child")

    page = B()
    page.create()
    page.source.body().widget()
    assert "child" in page.render()
    assert "parent" not in page.render()


def test_struct_method_dispatched_via_active_builder():
    """A struct method is resolved through the builder of the node it is
    invoked on. Defined on an SVG page, it is reachable from an SVG node
    and its ``pane.<tag>`` calls resolve in the SVG grammar."""

    class P(SvgBuilder):
        @struct_method
        def stamp(self, pane, label):
            pane.rect(width=10, height=10)
            pane.text(label, x=0, y=20)

        def main(self, root):
            pass

    page = P()
    page.create()
    svg = page.source.svg(viewBox="0 0 100 100")
    svg.stamp("hi")
    out = page.render()
    assert "<rect" in out
    assert "<text" in out
    assert ">hi<" in out


def test_struct_method_return_value_passed_through():
    class P(HtmlBuilder):
        @struct_method
        def card(self, pane, title):
            pane.h2(title)
            return pane.div(class_="body")

        def main(self, root):
            pass

    page = P()
    page.create()
    body_inner = page.source.body().card("Hello")
    body_inner.p("inside")
    out = page.render()
    assert "<h2>Hello</h2>" in out
    assert 'class="body"' in out
    assert "<p>inside</p>" in out
