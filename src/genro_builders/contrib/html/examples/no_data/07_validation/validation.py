# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""07 — Structure validation: a grammar constrains the tree. See readme.md."""
from __future__ import annotations

from typing import Annotated

from genro_builders.builder import BuilderBase, Range, Regex, abstract, element


class CustomPage(BuilderBase):
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

    def main(self, root):
        r = root.recipe()
        r.ingredient("flour", qty=500)
        r.ingredient("water", qty=300)
        r.step("Mix flour and water")
        r.step("Knead for ten minutes")


def _capture(fn):
    """Run a builder action expected to fail; return the error message."""
    try:
        fn()
    except (ValueError, TypeError) as err:
        return f"{type(err).__name__}: {err}"
    return "(no error — unexpected)"


def _bad_parent():
    CustomPage().source.step("orphan step")  # step requires parent 'recipe'


def _bad_qty():
    CustomPage().source.recipe().ingredient("salt", qty=-5)  # Range(gt=0)


if __name__ == "__main__":
    page = CustomPage()
    page.set_render_target("output.xml")
    page.create()
    page.render(pretty=True)
    print("<!-- valid recipe -->")
    print(page.rendered_target)
    print("<!-- step outside recipe (parent_tags) -->")
    print(_capture(_bad_parent))
    print("<!-- negative qty (Range validator) -->")
    print(_capture(_bad_qty))
