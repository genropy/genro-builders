# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0

"""SundayLunchMenu - Example menu using ChefApp.

Demonstrates:
- Course structure (first_courses, main_courses, side_dishes, desserts, pizzas, drinks)
- Dishes with ingredients
- Components (meat_sauce, white_sauce)
- Cardinality constraints (pizza toppings)
- Abstract inheritance (base_dish)
"""

from __future__ import annotations

from genro_builders.builder_bag import BuilderBag as Bag

from ..chef_app import ChefApp


class SundayLunchMenu(ChefApp):
    """Traditional Sunday Lunch menu."""

    def main(self, menu: Bag) -> None:
        # -----------------------------------------------------------------
        # FIRST COURSES
        # -----------------------------------------------------------------
        first_courses = menu.first_courses()

        # Lasagne with nested components (3 levels deep)
        # lasagne_sauce contains: meat_sauce (which contains soffritto) + white_sauce
        lasagne = first_courses.pasta(name="Bolognese Lasagne", servings=6)
        lasagne.lasagne_sauce()  # 3 levels: lasagne_sauce -> meat_sauce -> soffritto
        lasagne.ingredient("fresh pasta sheets", quantity="500g")
        lasagne.ingredient("parmesan cheese", quantity="150g")
        lasagne.note("Layer: pasta, meat sauce, white sauce, repeat")

        # Risotto - component has base ingredients, we add only extras
        risotto = first_courses.risotto(name="Porcini Mushroom Risotto", servings=4)
        risotto.ingredient("porcini mushrooms", quantity="200g")  # Extra ingredient

        # -----------------------------------------------------------------
        # MAIN COURSES
        # -----------------------------------------------------------------
        main_courses = menu.main_courses()

        # Meat dish - component has base (olive oil, salt, pepper), we add specifics
        roast = main_courses.meat_dish(name="Roast Veal", servings=6)
        roast.ingredient("veal roast", quantity="1.2kg")
        roast.ingredient("rosemary", quantity="2 sprigs")
        roast.ingredient("garlic", quantity="4 cloves")
        roast.ingredient("white wine", quantity="200ml")
        roast.cooking_method("roast at 180C for 90 minutes")

        # -----------------------------------------------------------------
        # SIDE DISHES
        # -----------------------------------------------------------------
        side_dishes = menu.side_dishes()

        # Vegetable - component has base (olive oil, salt), we add specifics
        potatoes = side_dishes.vegetable(name="Roasted Potatoes")
        potatoes.ingredient("potatoes", quantity="1kg")
        potatoes.ingredient("rosemary", quantity="fresh")

        # Salad - component has base (olive oil, vinegar, salt), we add specifics
        salad = side_dishes.salad(name="Mixed Salad")
        salad.ingredient("mixed greens", quantity="200g")
        salad.ingredient("cherry tomatoes", quantity="150g")

        # -----------------------------------------------------------------
        # DESSERTS
        # -----------------------------------------------------------------
        desserts = menu.desserts()

        # Cake - component has base (flour, sugar, eggs, butter), tiramisu replaces
        tiramisu = desserts.cake(name="Tiramisu", servings=8)
        tiramisu.ingredient("mascarpone cheese", quantity="500g")
        tiramisu.ingredient("ladyfinger biscuits", quantity="300g")
        tiramisu.ingredient("espresso coffee", quantity="300ml")
        tiramisu.ingredient("cocoa powder", quantity="for dusting")

        # -----------------------------------------------------------------
        # PIZZAS
        # -----------------------------------------------------------------
        pizzas = menu.pizzas()

        margherita = pizzas.pizza(name="Margherita")
        margherita.sauce("San Marzano tomato")
        margherita.cheese("buffalo mozzarella")
        margherita.topping("fresh basil")

        # -----------------------------------------------------------------
        # DRINKS
        # -----------------------------------------------------------------
        drinks = menu.drinks()
        drinks.wine("Chianti Classico DOCG")
        drinks.wine("Prosecco DOC")
        drinks.soft_drink("Sparkling water")


if __name__ == "__main__":
    app = SundayLunchMenu(name="Sunday Lunch")
    # Print the pure recipe as XML
    print(app.store.to_xml())
