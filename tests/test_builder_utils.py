# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for builder_utils — quick_ref text generation."""

from genro_builders import BagBuilderBase
from genro_builders.builder_utils import quick_ref
from genro_builders.builders import abstract, component, element


class SimpleBuilder(BagBuilderBase):
    @abstract(sub_tags="heading,text")
    def flow(self): ...

    @element()
    def heading(self): ...

    @element(sub_tags="")
    def text(self): ...

    @element(parent_tags="flow")
    def link(self): ...

    @component()
    def card(self, comp, title=None):
        comp.heading(title)
        comp.text("content")


class TestQuickRef:
    """Tests for quick_ref() text generation."""

    def test_returns_string(self):
        """quick_ref returns a string."""
        from genro_builders.builder_bag import BuilderBag as Bag

        bag = Bag(builder=SimpleBuilder)
        result = quick_ref(bag.builder)
        assert isinstance(result, str)

    def test_contains_class_name(self):
        """Default title uses builder class name."""
        from genro_builders.builder_bag import BuilderBag as Bag

        bag = Bag(builder=SimpleBuilder)
        result = quick_ref(bag.builder)
        assert "SimpleBuilder" in result

    def test_custom_title(self):
        """Custom title replaces class name."""
        from genro_builders.builder_bag import BuilderBag as Bag

        bag = Bag(builder=SimpleBuilder)
        result = quick_ref(bag.builder, title="My Builder")
        assert "My Builder" in result
        assert "SimpleBuilder" not in result

    def test_abstract_section(self):
        """Abstract elements appear in ABSTRACT section with @ prefix."""
        from genro_builders.builder_bag import BuilderBag as Bag

        bag = Bag(builder=SimpleBuilder)
        result = quick_ref(bag.builder)
        assert "ABSTRACT" in result
        assert "@flow" in result

    def test_elements_section(self):
        """Regular elements appear in ELEMENTS section."""
        from genro_builders.builder_bag import BuilderBag as Bag

        bag = Bag(builder=SimpleBuilder)
        result = quick_ref(bag.builder)
        assert "ELEMENTS" in result
        assert "heading" in result
        assert "text" in result

    def test_components_section(self):
        """Components appear in COMPONENTS section."""
        from genro_builders.builder_bag import BuilderBag as Bag

        bag = Bag(builder=SimpleBuilder)
        result = quick_ref(bag.builder)
        assert "COMPONENTS" in result
        assert "card" in result

    def test_sub_tags_displayed(self):
        """sub_tags parameter is shown in output."""
        from genro_builders.builder_bag import BuilderBag as Bag

        bag = Bag(builder=SimpleBuilder)
        result = quick_ref(bag.builder)
        assert 'sub_tags="heading,text"' in result

    def test_empty_sub_tags_displayed(self):
        """Empty sub_tags (void element) is shown."""
        from genro_builders.builder_bag import BuilderBag as Bag

        bag = Bag(builder=SimpleBuilder)
        result = quick_ref(bag.builder)
        assert 'sub_tags=""' in result

    def test_parent_tags_displayed(self):
        """parent_tags parameter is shown in output."""
        from genro_builders.builder_bag import BuilderBag as Bag

        bag = Bag(builder=SimpleBuilder)
        result = quick_ref(bag.builder)
        assert 'parent_tags="flow"' in result

    def test_documentation_displayed(self):
        """Documentation string first line is shown."""
        from genro_builders.builder_bag import BuilderBag as Bag

        class DocBuilder(BagBuilderBase):
            @element()
            def item(self):
                """A list item element."""

        bag = Bag(builder=DocBuilder)
        result = quick_ref(bag.builder)
        assert "A list item element." in result

    def test_empty_builder(self):
        """Builder with only data_elements produces no sections."""
        from genro_builders.builder_bag import BuilderBag as Bag

        class EmptyBuilder(BagBuilderBase):
            pass

        bag = Bag(builder=EmptyBuilder)
        result = quick_ref(bag.builder)
        assert "Quick Reference" in result


