# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""07 — Structure validation. See README.md for the walkthrough.

A small custom dialect (``recipe``) shows how a grammar constrains
structure: parent_tags, sub_tags cardinality, abstract/inherits_from,
and call-argument validation from the element signature.
"""
from __future__ import annotations

from typing import Annotated

from genro_builders.builder import (
    BuilderBase,
    BuilderHandler,
    Range,
    Regex,
    abstract,
    element,
)


class RecipeBuilder(BuilderBase):
    """Toy grammar: a recipe with a title, ingredients and ordered steps."""

    _name = "recipe"
    _default_render_mode = "xml"

    @abstract(sub_tags="*")
    def titled(self): ...

    @element(sub_tags="ingredient[1:],step[1:]", inherits_from="titled")
    def recipe(self): ...

    @element(parent_tags="recipe")
    def ingredient(
        self,
        node_value: str | None = None,
        qty: Annotated[float, Range(gt=0)] | None = None,
    ): ...

    @element(parent_tags="recipe")
    def step(
        self,
        node_value: Annotated[str, Regex(r".+")] | None = None,
    ): ...


class RecipeHandler(BuilderHandler):
    builder_class = RecipeBuilder


def _build_valid():
    h = RecipeHandler()
    r = h.source.recipe()
    r.ingredient("flour", qty=500)
    r.ingredient("water", qty=300)
    r.step("Mix flour and water")
    r.step("Knead for ten minutes")
    return h.render()


def _capture(fn):
    """Run a builder action expected to fail; return the error message."""
    try:
        fn()
    except (ValueError, TypeError) as err:
        return f"{type(err).__name__}: {err}"
    return "(no error — unexpected)"


def _bad_parent():
    h = RecipeHandler()
    h.source.step("orphan step")  # step requires parent 'recipe'


def _bad_qty():
    h = RecipeHandler()
    r = h.source.recipe()
    r.ingredient("salt", qty=-5)  # Range(gt=0) violated


if __name__ == "__main__":
    parts = [
        "<!-- Valid recipe -->",
        _build_valid(),
        "",
        "<!-- step outside recipe (parent_tags) -->",
        _capture(_bad_parent),
        "",
        "<!-- negative qty (Range validator) -->",
        _capture(_bad_qty),
        "",
    ]
    rendered = "\n".join(parts)
    print(rendered)
