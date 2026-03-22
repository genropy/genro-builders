# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0

"""MenuBuilder - Didactic example demonstrating builder syntax possibilities.

This module showcases the full range of @element, @abstract, and @component
decorator capabilities through a restaurant menu domain.

SYNTAX EXAMPLES:

1. ELEMENTS - Pure declarative (empty body)

   @element()
   def ingredient(self): ...

   @element(sub_tags="pasta, risotto, soup")      # allowed children
   def first_courses(self): ...

   @element(sub_tags="*")                         # wildcard: any children allowed
   def container(self): ...

   @element(sub_tags="")                          # closed/leaf, no children
   def ingredient(self): ...

   @element(parent_tags="pizza")                  # restricted parent
   def topping(self): ...

   @element(sub_tags="cheese[:1], topping[1:3]")  # cardinality: max 1, 1-3
   def pizza(self): ...

   @element(tags="salt, pepper, oil, vinegar")    # multiple tags -> same handler
   def condiment(self): ...

2. ABSTRACT - Base elements for inheritance

   @abstract(sub_tags="ingredient")               # cannot be used directly
   def base_dish(self): ...

   @element(inherits_from="base_dish")            # inherits sub_tags
   def pasta(self): ...

3. COMPONENTS - Reusable logic (body executes at compile time)

   @component(sub_tags="")                        # closed, returns parent
   def meat_sauce(self, comp: Bag, **kwargs) -> Bag:
       comp.ingredient("ground beef", quantity="500g")
       return comp

   @component(sub_tags="ingredient")              # open, returns internal bag
   def custom_sauce(self, comp: Bag, **kwargs) -> Bag:
       comp.ingredient("base")
       return comp  # caller can add more

   @component(builder=IngredientBuilder)          # internal bag uses different builder
   def special_recipe(self, comp: Bag, **kwargs) -> Bag:
       comp.item("special")
       return comp

4. NESTED COMPONENTS - Components using other components (N levels)

   @component(sub_tags="")
   def soffritto(self, comp: Bag, **kwargs) -> Bag:
       comp.ingredient("onion")
       comp.ingredient("carrot")
       comp.ingredient("celery")
       return comp

   @component(sub_tags="soffritto, ingredient")   # can contain soffritto
   def meat_sauce(self, comp: Bag, **kwargs) -> Bag:
       comp.soffritto()                           # nested component
       comp.ingredient("ground beef")
       return comp

   @component(sub_tags="")
   def lasagne_sauce(self, comp: Bag, **kwargs) -> Bag:
       comp.meat_sauce()                          # 2 levels: meat_sauce -> soffritto
       comp.white_sauce()
       return comp

   # Result: lasagne_sauce contains meat_sauce which contains soffritto
   # All expansion happens lazily during compile(), recursively

HIERARCHY:

    menu
      |-- first_courses
      |     |-- pasta -> ingredient, meat_sauce, white_sauce
      |     |-- risotto -> ingredient
      |     +-- soup -> ingredient
      |-- main_courses
      |     |-- meat_dish -> ingredient, cooking_method
      |     +-- fish_dish -> ingredient, cooking_method
      |-- side_dishes
      |     +-- vegetable -> ingredient
      |-- desserts
      |     +-- cake, ice_cream -> ingredient
      +-- pizzas
            +-- pizza -> topping, cheese

LAZY EXPANSION (Pure Bag Architecture):

    Components are NOT expanded at creation time.
    When you call menu.first_courses().pasta().meat_sauce(), the meat_sauce node
    is created but its body is NOT executed. The body executes only during compile().

    This means the source Bag is a "pure recipe" - exactly what you wrote.
"""

from __future__ import annotations

from genro_builders import BagBuilderBase
from genro_builders.builder_bag import BuilderBag as Bag
from genro_builders.builders import abstract, component, element


# =============================================================================
# Auxiliary builder for demonstrating builder override in components
# =============================================================================


class IngredientBuilder(BagBuilderBase):
    """Specialized builder for ingredient-only contexts."""

    @element(sub_tags="")
    def item(self): ...

    @element(sub_tags="")
    def quantity(self): ...

    @element(sub_tags="")
    def unit(self): ...


# =============================================================================
# Main MenuBuilder
# =============================================================================


class MenuBuilder(BagBuilderBase):
    """Builder for restaurant menu structures.

    Demonstrates:
    - Hierarchical structure with sub_tags
    - Abstract base elements with inheritance
    - Components for reusable recipes
    - Cardinality constraints
    - Multiple tags mapping to same handler
    - Parent restrictions with parent_tags
    """

    # =========================================================================
    # TOP LEVEL - Menu root
    # =========================================================================

    @element(sub_tags="first_courses, main_courses, side_dishes, desserts, pizzas, drinks")
    def menu(self): ...

    # =========================================================================
    # COURSE CATEGORIES
    # =========================================================================

    @element(sub_tags="pasta, risotto, soup, meat_sauce, white_sauce, lasagne_sauce")
    def first_courses(self): ...

    @element(sub_tags="meat_dish, fish_dish")
    def main_courses(self): ...

    @element(sub_tags="vegetable, salad")
    def side_dishes(self): ...

    @element(sub_tags="cake, ice_cream, fruit")
    def desserts(self): ...

    @element(sub_tags="pizza")
    def pizzas(self): ...

    @element(sub_tags="wine, beer, soft_drink")
    def drinks(self): ...

    # =========================================================================
    # ABSTRACT BASE ELEMENTS
    # =========================================================================

    @abstract(sub_tags="ingredient, note")
    def base_dish(self): ...

    @abstract(sub_tags="ingredient")
    def base_sauce(self): ...

    # =========================================================================
    # DISH COMPONENTS - Base recipes with default ingredients (open, user can add more)
    # =========================================================================

    # First courses
    @component(sub_tags="ingredient, meat_sauce, white_sauce, lasagne_sauce, note")
    def pasta(self, comp: Bag, **kwargs) -> Bag:
        """Fresh pasta base."""
        comp.ingredient("fresh pasta", quantity="500g")
        comp.ingredient("salt", quantity="to taste")
        return comp

    @component(sub_tags="ingredient, note")
    def risotto(self, comp: Bag, **kwargs) -> Bag:
        """Risotto base with arborio rice."""
        comp.ingredient("arborio rice", quantity="320g")
        comp.ingredient("butter", quantity="50g")
        comp.ingredient("parmesan cheese", quantity="80g")
        comp.ingredient("vegetable broth", quantity="1L")
        comp.ingredient("white wine", quantity="100ml")
        return comp

    @component(sub_tags="ingredient, note")
    def soup(self, comp: Bag, **kwargs) -> Bag:
        """Soup base."""
        comp.ingredient("vegetable broth", quantity="1.5L")
        comp.ingredient("olive oil", quantity="2 tbsp")
        comp.ingredient("salt", quantity="to taste")
        return comp

    # Main courses
    @component(sub_tags="ingredient, cooking_method, note")
    def meat_dish(self, comp: Bag, **kwargs) -> Bag:
        """Meat dish base."""
        comp.ingredient("olive oil", quantity="2 tbsp")
        comp.ingredient("salt", quantity="to taste")
        comp.ingredient("pepper", quantity="to taste")
        return comp

    @component(sub_tags="ingredient, cooking_method, note")
    def fish_dish(self, comp: Bag, **kwargs) -> Bag:
        """Fish dish base."""
        comp.ingredient("olive oil", quantity="2 tbsp")
        comp.ingredient("lemon", quantity="1")
        comp.ingredient("salt", quantity="to taste")
        return comp

    # Side dishes
    @component(sub_tags="ingredient, note")
    def vegetable(self, comp: Bag, **kwargs) -> Bag:
        """Vegetable side dish base."""
        comp.ingredient("olive oil", quantity="2 tbsp")
        comp.ingredient("salt", quantity="to taste")
        return comp

    @component(sub_tags="ingredient, note")
    def salad(self, comp: Bag, **kwargs) -> Bag:
        """Salad base."""
        comp.ingredient("olive oil", quantity="2 tbsp")
        comp.ingredient("vinegar", quantity="1 tbsp")
        comp.ingredient("salt", quantity="to taste")
        return comp

    # Desserts
    @component(sub_tags="ingredient, note")
    def cake(self, comp: Bag, **kwargs) -> Bag:
        """Cake base."""
        comp.ingredient("flour", quantity="250g")
        comp.ingredient("sugar", quantity="200g")
        comp.ingredient("eggs", quantity="3")
        comp.ingredient("butter", quantity="100g")
        return comp

    @component(sub_tags="ingredient, note")
    def ice_cream(self, comp: Bag, **kwargs) -> Bag:
        """Ice cream base."""
        comp.ingredient("milk", quantity="500ml")
        comp.ingredient("cream", quantity="250ml")
        comp.ingredient("sugar", quantity="150g")
        return comp

    @component(sub_tags="ingredient, note")
    def fruit(self, comp: Bag, **kwargs) -> Bag:
        """Fresh fruit base."""
        return comp  # No base ingredients, user specifies fruits

    # =========================================================================
    # PIZZA with cardinality constraints
    # =========================================================================

    @element(sub_tags="cheese[:1], topping[1:], sauce[:1], ingredient")
    def pizza(self): ...

    @element(sub_tags="", parent_tags="pizza")
    def topping(self): ...

    @element(sub_tags="", parent_tags="pizza")
    def cheese(self): ...

    @element(sub_tags="", parent_tags="pizza")
    def sauce(self): ...

    # =========================================================================
    # DRINKS with tags parameter (multiple tags -> same handler)
    # =========================================================================

    @element(tags="wine, beer, soft_drink", sub_tags="")
    def beverage(self): ...

    # =========================================================================
    # LEAF ELEMENTS (sub_tags="" means closed/no children)
    # =========================================================================

    @element(sub_tags="")
    def ingredient(self): ...

    @element(sub_tags="")
    def note(self): ...

    @element(sub_tags="")
    def cooking_method(self): ...

    # =========================================================================
    # COMPONENTS - Reusable recipes (lazy expansion)
    # =========================================================================

    # -------------------------------------------------------------------------
    # BASE COMPONENTS - Low-level reusable building blocks
    # -------------------------------------------------------------------------

    @component(sub_tags="")
    def soffritto(self, comp: Bag, **kwargs) -> Bag:
        """Italian flavor base (mirepoix).

        Used by many sauces and dishes. Demonstrates component reuse.
        """
        comp.ingredient("onion", quantity="1")
        comp.ingredient("carrot", quantity="1")
        comp.ingredient("celery", quantity="1 stalk")
        comp.ingredient("olive oil", quantity="2 tbsp")
        return comp

    # -------------------------------------------------------------------------
    # SAUCE COMPONENTS - Can use other components (nested)
    # -------------------------------------------------------------------------

    @component(sub_tags="soffritto, ingredient")
    def meat_sauce(self, comp: Bag, **kwargs) -> Bag:
        """Bolognese-style meat sauce.

        NESTED COMPONENTS: Uses soffritto as base, then adds meat sauce specifics.
        This demonstrates components using other components.

        The soffritto component body is NOT expanded here - it remains a node.
        Expansion happens only during compile(), recursively.
        """
        comp.soffritto()  # Nested component - lazy, not expanded yet
        comp.ingredient("ground beef", quantity="500g")
        comp.ingredient("tomato passata", quantity="400g")
        comp.ingredient("red wine", quantity="100ml")
        return comp

    @component(sub_tags="")
    def white_sauce(self, comp: Bag, **kwargs) -> Bag:
        """Bechamel white sauce.

        Reusable across dishes: lasagne, crepes, cannelloni, etc.
        sub_tags="" means this is closed - returns parent for chaining.
        """
        comp.ingredient("milk", quantity="500ml")
        comp.ingredient("butter", quantity="50g")
        comp.ingredient("flour", quantity="50g")
        comp.ingredient("nutmeg", quantity="a pinch")
        comp.ingredient("salt", quantity="to taste")
        return comp

    @component(sub_tags="")
    def lasagne_sauce(self, comp: Bag, **kwargs) -> Bag:
        """Combined sauce for lasagne - 3 LEVELS OF NESTING.

        Hierarchy when expanded:
            lasagne_sauce
              |-- meat_sauce          <- level 2
              |     +-- soffritto     <- level 3
              |           |-- onion
              |           |-- carrot
              |           |-- celery
              |           +-- olive oil
              |     |-- ground beef
              |     |-- tomato passata
              |     +-- red wine
              +-- white_sauce         <- level 2
                    |-- milk
                    |-- butter
                    |-- flour
                    |-- nutmeg
                    +-- salt

        All expansion is LAZY - happens only during compile().
        """
        comp.meat_sauce()   # Contains soffritto (3 levels deep)
        comp.white_sauce()
        return comp

    @component(sub_tags="ingredient")
    def custom_sauce(self, comp: Bag, base: str = "tomato", **kwargs) -> Bag:
        """Custom sauce - open component.

        sub_tags="ingredient" means this is open - returns internal bag.
        Caller can add more ingredients after the base ones.

        Example:
            sauce = pasta.custom_sauce(base="cream")
            sauce.ingredient("mushrooms")  # add to the component
        """
        comp.ingredient(base, quantity="base")
        return comp

    @component(builder=IngredientBuilder, sub_tags="")
    def molecular_recipe(self, comp: Bag, technique: str = "spherification", **kwargs) -> Bag:
        """Component with builder override.

        The internal bag uses IngredientBuilder instead of MenuBuilder.
        This allows specialized elements (item, quantity, unit) inside.
        """
        comp.item(technique)
        comp.quantity("as needed")
        comp.unit("ml")
        return comp


# =============================================================================
# Usage examples (not executed, just for documentation)
# =============================================================================

"""
EXAMPLE USAGE:

    from genro_builders.builder_bag import BuilderBag as Bag
    from examples.builders.chef_app import MenuBuilder

    # Create a menu
    store = Bag(builder=MenuBuilder)
    menu = store.menu(name="Sunday Lunch")

    # Add first courses
    first = menu.first_courses()

    # Pasta with components (lazy - not expanded yet)
    lasagne = first.pasta(name="Bolognese Lasagne", servings=4)
    lasagne.meat_sauce()   # Component node created, body NOT executed
    lasagne.white_sauce()  # Component node created, body NOT executed
    lasagne.ingredient("fresh pasta sheets", quantity="500g")
    lasagne.ingredient("parmesan cheese", quantity="100g")

    # Risotto with ingredients
    risotto = first.risotto(name="Mushroom Risotto")
    risotto.ingredient("arborio rice", quantity="320g")
    risotto.ingredient("porcini mushrooms", quantity="200g")
    risotto.ingredient("vegetable broth", quantity="1L")

    # Add pizzas with cardinality
    pizzas = menu.pizzas()
    margherita = pizzas.pizza(name="Margherita")
    margherita.sauce("tomato")       # max 1 sauce
    margherita.cheese("mozzarella")  # max 1 cheese
    margherita.topping("basil")      # at least 1 topping

    # At this point, the Bag contains the "pure recipe":
    # - meat_sauce and white_sauce are nodes with handler_name
    # - Their bodies have NOT been executed
    # - Expansion happens only during compile()

HIERARCHY VISUALIZATION:

    menu (name="Sunday Lunch")
    |-- first_courses
    |   |-- pasta (name="Bolognese Lasagne", servings=4)
    |   |   |-- meat_sauce      <- component, not expanded
    |   |   |-- white_sauce     <- component, not expanded
    |   |   |-- ingredient (quantity="500g") = "fresh pasta sheets"
    |   |   +-- ingredient (quantity="100g") = "parmesan cheese"
    |   +-- risotto (name="Mushroom Risotto")
    |       |-- ingredient (quantity="320g") = "arborio rice"
    |       |-- ingredient (quantity="200g") = "porcini mushrooms"
    |       +-- ingredient (quantity="1L") = "vegetable broth"
    +-- pizzas
        +-- pizza (name="Margherita")
            |-- sauce = "tomato"
            |-- cheese = "mozzarella"
            +-- topping = "basil"
"""
