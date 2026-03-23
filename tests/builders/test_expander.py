# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for the component expander pipeline."""

from __future__ import annotations

import pytest

from genro_builders.builder_bag import BuilderBag as Bag
from genro_builders.expander import expand


class TestExpanderBasic:
    """Basic expander tests with simple components."""

    def test_expand_no_components(self):
        """Bag without components yields same nodes as walk."""
        from genro_builders.builders.html import HtmlBuilder

        bag = Bag(builder=HtmlBuilder)
        bag.div()
        bag.p("Hello")

        # Collect paths from both
        walk_paths = [path for path, _ in bag.walk()]
        expand_paths = [path for path, _ in expand(bag)]

        assert walk_paths == expand_paths

    def test_expand_without_builder(self):
        """Bag without builder just yields from walk."""
        bag = Bag()
        bag.set_item("a", 1)
        bag.set_item("b", 2)

        paths = [path for path, _ in expand(bag)]
        assert paths == ["a", "b"]


class TestExpanderMenuBuilder:
    """Test expander with MenuBuilder's nested components."""

    @pytest.fixture
    def menu_bag(self):
        """Create a menu bag with nested components."""
        from examples.builders.chef_app.menu_builder import MenuBuilder

        bag = Bag(builder=MenuBuilder)
        menu = bag.menu(name="Test Menu")

        first_courses = menu.first_courses()

        # This creates nested components:
        # lasagne_sauce -> meat_sauce -> soffritto
        pasta = first_courses.pasta(name="Lasagne")
        pasta.lasagne_sauce()

        return bag

    def test_expand_nested_components(self, menu_bag):
        """Expander should expand nested components recursively."""
        # Collect all expanded paths and tags
        expanded = [(path, node.node_tag) for path, node in expand(menu_bag)]

        # After expansion, we should see ingredients from:
        # 1. pasta base (fresh pasta, salt)
        # 2. lasagne_sauce body which contains:
        #    - meat_sauce body which contains:
        #      - soffritto body (onion, carrot, celery, olive oil)
        #      - ground beef, tomato passata, red wine
        #    - white_sauce body (milk, butter, flour, nutmeg, salt)

        # Extract just the tags
        tags = [tag for _, tag in expanded]

        # We should have many ingredients from the expansion
        ingredient_count = tags.count("ingredient")

        # Soffritto has 4 ingredients
        # Meat sauce adds 3 more
        # White sauce has 5
        # Pasta base has 2
        # Total: 14 ingredients (approximately, depends on exact MenuBuilder)
        assert ingredient_count >= 10, f"Expected many ingredients, got {ingredient_count}"

        # The component tags should NOT appear in expanded output
        # (they are replaced by their body contents)
        assert "soffritto" not in tags, "soffritto should be expanded, not yielded as-is"
        assert "meat_sauce" not in tags, "meat_sauce should be expanded, not yielded as-is"
        assert "white_sauce" not in tags, "white_sauce should be expanded, not yielded as-is"

    def test_expand_based_on_component(self):
        """based_on component extends the base with additional content."""
        from genro_builders import BagBuilderBase
        from genro_builders.builders import component, element

        class Builder(BagBuilderBase):
            @element()
            def ingredient(self): ...

            @component()
            def risotto(self, comp, **kwargs):
                comp.ingredient("arborio rice", quantity="320g")
                comp.ingredient("butter", quantity="50g")

            @component(based_on="risotto")
            def mushroom_risotto(self, comp, **kwargs):
                comp.ingredient("porcini mushrooms", quantity="200g")

        bag = Bag(builder=Builder)
        bag.mushroom_risotto(name="Mushroom Risotto")

        # Expand and collect
        expanded = list(expand(bag))

        # Find all ingredient values
        ingredient_values = [
            node.value for _, node in expanded if node.node_tag == "ingredient"
        ]

        # Should contain both base risotto ingredients AND the extended one
        assert "porcini mushrooms" in ingredient_values
        assert "arborio rice" in ingredient_values  # From risotto base
        assert "butter" in ingredient_values  # From risotto base


class TestExpanderEdgeCases:
    """Edge cases for the expander."""

    def test_expand_empty_bag(self):
        """Empty bag yields nothing."""
        bag = Bag()
        expanded = list(expand(bag))
        assert expanded == []

    def test_expand_deeply_nested(self):
        """Test with deeply nested structure (non-component)."""
        from genro_builders.builders.html import HtmlBuilder

        bag = Bag(builder=HtmlBuilder)
        div1 = bag.div()
        div2 = div1.div()
        div3 = div2.div()
        div3.p("Deep content")

        paths = [path for path, _ in expand(bag)]

        assert "div_0" in paths
        assert "div_0.div_0" in paths
        assert "div_0.div_0.div_0" in paths
        assert "div_0.div_0.div_0.p_0" in paths
