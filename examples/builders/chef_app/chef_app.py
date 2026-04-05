# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0

"""ChefApp - Base class for menu applications built with MenuBuilder.

This module demonstrates the app pattern for using MULTIPLE builders:
1. MenuBuilder for defining the recipe (pure Bag)
2. ReportLabBuilder for printing customer-friendly menus (PDF output)

Example:
    from examples.builders.chef_app import ChefApp

    class SundayLunch(ChefApp):
        def main(self, menu):
            first = menu.first_courses()
            lasagne = first.pasta(name="Bolognese Lasagne")
            lasagne.lasagne_sauce()
            lasagne.ingredient("fresh pasta sheets", quantity="500g")

    app = SundayLunch(name="Sunday Lunch")
    app.print_menu("sunday_menu.pdf")  # Uses ReportLabBuilder
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from genro_builders.builder_bag import BuilderBag as Bag

from .menu_builder import MenuBuilder


class ChefApp:
    """Base class for menu applications.

    Subclass and override recipe(menu) to define your menu.
    The menu is a Bag with MenuBuilder - a pure recipe.
    """

    def __init__(self, name: str = "Menu") -> None:
        self._store = Bag(builder=MenuBuilder)
        self._menu = self._store.menu(name=name)
        self.main(self._menu)

    @property
    def store(self) -> Bag:
        """The root Bag containing the menu."""
        return self._store

    @property
    def menu(self) -> Bag:
        """The menu Bag (returned by menu() element)."""
        return self._menu

    def main(self, menu: Bag) -> None:
        """Override to build your menu.

        Args:
            menu: The menu Bag. Add courses by calling methods on it.
        """

    def print_menu(self, destination: str | Path | None = None) -> bytes | None:
        """Print a customer-friendly menu using ReportLabBuilder.

        Uses a SECOND builder (ReportLabBuilder) to generate a PDF menu
        from the recipe Bag. Demonstrates multi-builder architecture.

        Args:
            destination: Optional file path. If None, returns PDF bytes.

        Returns:
            PDF bytes if destination is None, otherwise None.
        """
        try:
            from genro_print.builders import ReportLabBuilder
        except ImportError as e:
            msg = "genro-print required: pip install genro-print"
            raise ImportError(msg) from e

        # Get menu name from attributes
        menu_node = self._store.get_node("menu")
        menu_name = menu_node.attr.get("name", "Menu") if menu_node else "Menu"

        # Build PDF using ReportLabBuilder
        doc = Bag(builder=ReportLabBuilder)
        doc.document(title=menu_name)

        # Title
        doc.paragraph(f"<b>{menu_name}</b>", style="Title")
        doc.spacer(height=10.0)

        # Process each course category
        self._print_courses(doc, self._menu)

        # Build and render
        doc.builder.build()
        pdf_bytes = doc.builder.render()

        if destination:
            Path(destination).write_bytes(pdf_bytes)
            return None

        return pdf_bytes

    def _print_courses(self, doc: Any, menu_bag: Any) -> None:
        """Add courses to the PDF document."""
        # Course names mapping for nice display
        course_titles = {
            "first_courses": "First Courses",
            "main_courses": "Main Courses",
            "side_dishes": "Side Dishes",
            "desserts": "Desserts",
            "pizzas": "Pizzas",
            "drinks": "Drinks",
        }

        # menu_bag might be a BagNode, get its value (which is a Bag)
        courses = menu_bag.value if hasattr(menu_bag, "value") else menu_bag
        if not isinstance(courses, Bag):
            return

        for course_node in courses:
            tag = course_node.tag or ""
            if tag not in course_titles:
                continue

            # Check if course has dishes
            if not isinstance(course_node.value, Bag) or len(course_node.value) == 0:
                continue

            # Course header
            doc.paragraph(f"<b>{course_titles[tag]}</b>", style="Heading2")
            doc.spacer(height=3.0)

            # Each dish in the course
            for dish_node in course_node.value:
                self._print_dish(doc, dish_node)

            doc.spacer(height=5.0)

    def _print_dish(self, doc: Any, dish_node: Any) -> None:
        """Add a single dish to the PDF document."""
        # Dish name from attribute
        dish_name = dish_node.attr.get("name", dish_node.label.replace("_", " ").title())
        servings = dish_node.attr.get("servings")

        # Format dish line
        servings_str = f" (serves {servings})" if servings else ""
        doc.paragraph(f"    <b>{dish_name}</b>{servings_str}", style="Normal")
