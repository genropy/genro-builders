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
        from genro_builders.contrib.html import HtmlBuilder

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


class TestExpanderNestedComponents:
    """Test expander with 3-level nested components (inline builder)."""

    @pytest.fixture
    def nested_bag(self):
        """Create a bag with 3-level nested components: outer -> middle -> inner."""
        from genro_builders import BagBuilderBase
        from genro_builders.builders import component, element

        class NestedBuilder(BagBuilderBase):
            @element(sub_tags="item, outer_comp")
            def container(self): ...

            @element()
            def item(self): ...

            @component(sub_tags="")
            def inner_comp(self, comp, **kwargs):
                comp.item("inner_a")
                comp.item("inner_b")
                comp.item("inner_c")
                comp.item("inner_d")
                return comp

            @component(sub_tags="")
            def middle_comp(self, comp, **kwargs):
                comp.inner_comp()
                comp.item("middle_a")
                comp.item("middle_b")
                comp.item("middle_c")
                return comp

            @component(sub_tags="item")
            def outer_comp(self, comp, **kwargs):
                comp.middle_comp()
                comp.item("outer_a")
                comp.item("outer_b")
                comp.item("outer_c")
                return comp

        bag = Bag(builder=NestedBuilder)
        root = bag.container()
        root.outer_comp(name="test")

        return bag

    def test_expand_nested_components(self, nested_bag):
        """Expander should expand nested components recursively."""
        expanded = [(path, node.node_tag) for path, node in expand(nested_bag)]
        tags = [tag for _, tag in expanded]

        # inner_comp: 4 items, middle_comp: 3 items + inner, outer_comp: 3 items + middle
        # Total items after expansion: 4 + 3 + 3 = 10
        item_count = tags.count("item")
        assert item_count >= 10, f"Expected >= 10 items, got {item_count}"

        # Component tags should NOT appear in expanded output
        assert "inner_comp" not in tags, "inner_comp should be expanded"
        assert "middle_comp" not in tags, "middle_comp should be expanded"
        assert "outer_comp" not in tags, "outer_comp should be expanded"

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
        from genro_builders.contrib.html import HtmlBuilder

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
