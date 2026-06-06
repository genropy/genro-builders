# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for the reactive compute of data-elements (slice 1: first collect).

Scope: a single wave, value-update only (no ins/del, no container/child
binding). A data-element depends on a datum; when that datum changes, the
data-element is recomputed. Driven by ``_on_data_event`` on the update branch.

func resolution model (decided):
    - func is always a ``@staticmethod`` resolved by NAME via the handler's
      ``data_logic`` property (default: the handler itself; override: an
      instance or a list, searched left-to-right, first-wins);
    - a source that owns the name but NOT as staticmethod -> raise;
    - miss on all sources -> raise.

Signatures:
    - data_formula is PURE: ``func(**bindings)`` -> writes the return at
      ``destination``;
    - data_controller has side effects: ``func(node, **bindings)`` -> ``node``
      is explicit (no ``self``, the func is static).
"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

import pytest

from genro_builders.contrib.html import HtmlBuilderHandler


@contextmanager
def reactive(page_cls: type) -> Iterator[HtmlBuilderHandler]:
    """Start a page canonically and yield it inside a live() section.

    Reactivity lives inside an app: create, do the first render (which
    finishes startup and enables live), then enter live(). Mutations made
    on the yielded page inside the block drive the reactive cascade.
    """
    page = page_cls(application=object())
    page.create()
    page.render(target=False)
    with page.live(target=False):
        yield page


# ---------------------------------------------------------------------------
# formula recomputes on a dependency update
# ---------------------------------------------------------------------------


def test_formula_recomputes_on_dependency_update():
    """Changing a binding's datum recomputes the formula that reads it."""

    class P(HtmlBuilderHandler):
        @staticmethod
        def calc_area(base, altezza):
            return base * altezza / 2

        def main(self, root) -> None:
            body = root.body(datapath="tri")
            body.data_setter(".altezza", 6)
            body.data_setter(".base", 10)
            body.data_formula(
                ".area", "calc_area", base="^.base", altezza="^.altezza",
            )

    with reactive(P) as page:
        page.data.set_item("tri.altezza", 6)
        page.data.set_item("tri.base", 10)
        page.data.set_item("tri.base", 20)
    assert page.data.get_item("tri.area") == 60


def test_func_by_name_resolves_staticmethod():
    """``func`` given as a name resolves to a handler staticmethod and runs."""

    class P(HtmlBuilderHandler):
        @staticmethod
        def calc_area(base, altezza):
            return base * altezza / 2

        def main(self, root) -> None:
            body = root.body(datapath="tri")
            body.data_setter(".altezza", 4)
            body.data_setter(".base", 10)
            body.data_formula(
                ".area", "calc_area", base="^.base", altezza="^.altezza",
            )

    with reactive(P) as page:
        page.data.set_item("tri.altezza", 4)
        page.data.set_item("tri.base", 5)
        page.data.set_item("tri.base", 10)
    assert page.data.get_item("tri.area") == 20


# ---------------------------------------------------------------------------
# func resolution errors (compute-time, noisy)
# ---------------------------------------------------------------------------


def test_func_not_staticmethod_raises():
    """A name that resolves to a normal method (not static) raises at compute."""

    class P(HtmlBuilderHandler):
        def calc_area(self, base, altezza):  # normal method, not @staticmethod
            return base * altezza / 2

        def main(self, root) -> None:
            body = root.body(datapath="tri")
            body.data_setter(".altezza", 6)
            body.data_setter(".base", 10)
            body.data_formula(
                ".area", "calc_area", base="^.base", altezza="^.altezza",
            )

    with reactive(P) as page:
        page.data.set_item("tri.altezza", 6)
        page.data.set_item("tri.base", 10)
        with pytest.raises(TypeError):
            page.data.set_item("tri.base", 20)


def test_func_missing_raises():
    """A name absent from every data_logic source raises at compute."""

    class P(HtmlBuilderHandler):
        def main(self, root) -> None:
            body = root.body(datapath="tri")
            body.data_setter(".base", 10)
            body.data_formula(
                ".area", "nope", base="^.base",
            )

    with reactive(P) as page:
        page.data.set_item("tri.base", 10)
        with pytest.raises(AttributeError):
            page.data.set_item("tri.base", 20)


# ---------------------------------------------------------------------------
# data_logic resolution order
# ---------------------------------------------------------------------------


def test_data_logic_left_to_right_first_wins():
    """With several sources, the leftmost that owns the name wins."""

    class LogicA:
        @staticmethod
        def calc(base):
            return base * 2

    class LogicB:
        @staticmethod
        def calc(base):
            return base * 100

    class P(HtmlBuilderHandler):
        def _build_data_logic(self):
            return [LogicA(), LogicB()]

        def main(self, root) -> None:
            body = root.body(datapath="tri")
            body.data_setter(".base", 10)
            body.data_formula(".area", "calc", base="^.base")

    with reactive(P) as page:
        page.data.set_item("tri.base", 10)
        page.data.set_item("tri.base", 5)
    assert page.data.get_item("tri.area") == 10  # LogicA wins (5*2), not 500


def test_data_logic_skips_source_without_attr():
    """A source lacking the name is skipped; the next one provides it."""

    class LogicA:
        @staticmethod
        def something_else(base):
            return base

    class LogicB:
        @staticmethod
        def calc(base):
            return base * 3

    class P(HtmlBuilderHandler):
        def _build_data_logic(self):
            return [LogicA(), LogicB()]

        def main(self, root) -> None:
            body = root.body(datapath="tri")
            body.data_setter(".base", 10)
            body.data_formula(".area", "calc", base="^.base")

    with reactive(P) as page:
        page.data.set_item("tri.base", 10)
        page.data.set_item("tri.base", 7)
    assert page.data.get_item("tri.area") == 21  # LogicB.calc (7*3)


# ---------------------------------------------------------------------------
# controller receives node
# ---------------------------------------------------------------------------


def test_controller_receives_node():
    """A controller's func gets ``node`` first and may write the bag itself."""

    class P(HtmlBuilderHandler):
        @staticmethod
        def ctrl(node, base):
            node.set_relative_data(".doubled", base * 2)

        def main(self, root) -> None:
            body = root.body(datapath="tri")
            body.data_setter(".base", 10)
            body.data_controller("ctrl", base="^.base")

    with reactive(P) as page:
        page.data.set_item("tri.base", 10)
        page.data.set_item("tri.base", 9)
    assert page.data.get_item("tri.doubled") == 18


# ---------------------------------------------------------------------------
# view nodes are not recomputed
# ---------------------------------------------------------------------------


def test_view_node_not_recomputed():
    """A plain view node reading the same path is not a compute target."""

    class P(HtmlBuilderHandler):
        @staticmethod
        def calc_area(base):
            return base * 2

        def main(self, root) -> None:
            body = root.body(datapath="tri")
            body.data_setter(".base", 10)
            body.data_formula(".area", "calc_area", base="^.base")
            # a plain view node that reads the computed value
            body.p("^.area")

    with reactive(P) as page:
        page.data.set_item("tri.base", 10)
        page.data.set_item("tri.base", 4)
    # the formula recomputed (base*2)
    assert page.data.get_item("tri.area") == 8
    # the view <p> is not a data-element: it carries no destination/func and
    # is never executed as compute (it only re-renders).
    p_node = page.source.get_node_by_attr("tag", "p")
    assert p_node is None or not p_node.attr.get("_is_data_element")
