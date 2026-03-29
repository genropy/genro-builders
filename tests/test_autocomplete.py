# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for __dir__ autocompletion on BuilderBag, BuilderBagNode, ComponentProxy."""
from __future__ import annotations

from genro_builders.builder import BagBuilderBase, abstract, component, element
from genro_builders.builder_bag import BuilderBag
from genro_builders.component_proxy import ComponentProxy


class _TestBuilder(BagBuilderBase):
    """Builder with diverse sub_tags for autocompletion tests."""

    @abstract(sub_tags='extra_a, extra_b')
    def extensible(self): ...

    @element(sub_tags='child_a, child_b')
    def container(self): ...

    @element(sub_tags='*')
    def wildcard(self): ...

    @element(sub_tags='')
    def leaf(self): ...

    @element()
    def child_a(self): ...

    @element()
    def child_b(self): ...

    @element(sub_tags='', inherits_from='@extensible')
    def inheriting(self): ...

    @component(sub_tags='')
    def closed_comp(self, comp, **kwargs):
        return comp

    @component(sub_tags='child_a')
    def open_comp(self, comp, **kwargs):
        return comp

    @component(slots=['left', 'right'])
    def slotted_comp(self, comp, **kwargs):
        left = comp.container()
        right = comp.container()
        return {'left': left.value, 'right': right.value}


class TestBuilderBagDir:
    """Tests for BuilderBag.__dir__."""

    def test_bag_dir_includes_all_non_abstract_elements(self):
        bag = BuilderBag(builder=_TestBuilder)
        d = dir(bag)
        expected_elements = {
            'container', 'wildcard', 'leaf', 'child_a', 'child_b',
            'inheriting', 'closed_comp', 'open_comp', 'slotted_comp',
        }
        for name in expected_elements:
            assert name in d, f"'{name}' missing from dir(bag)"

    def test_bag_dir_excludes_abstract(self):
        bag = BuilderBag(builder=_TestBuilder)
        d = dir(bag)
        assert '@extensible' not in d

    def test_bag_dir_without_builder(self):
        bag = BuilderBag()
        d = dir(bag)
        assert isinstance(d, list)


class TestBuilderBagNodeDir:
    """Tests for BuilderBagNode.__dir__ — context-aware."""

    def test_node_dir_shows_only_sub_tags(self):
        bag = BuilderBag(builder=_TestBuilder)
        node = bag.container()
        d = dir(node)
        assert 'child_a' in d
        assert 'child_b' in d
        assert 'container' not in d
        assert 'wildcard' not in d
        assert 'leaf' not in d

    def test_node_dir_wildcard_shows_all(self):
        bag = BuilderBag(builder=_TestBuilder)
        node = bag.wildcard()
        d = dir(node)
        assert 'container' in d
        assert 'child_a' in d
        assert 'leaf' in d
        assert '@extensible' not in d

    def test_node_dir_leaf_shows_no_elements(self):
        bag = BuilderBag(builder=_TestBuilder)
        node = bag.leaf()
        d = dir(node)
        assert 'child_a' not in d
        assert 'container' not in d
        assert 'wildcard' not in d

    def test_node_dir_inherits_from_abstract(self):
        bag = BuilderBag(builder=_TestBuilder)
        node = bag.inheriting()
        d = dir(node)
        assert 'extra_a' in d
        assert 'extra_b' in d

    def test_node_dir_preserves_base_attributes(self):
        bag = BuilderBag(builder=_TestBuilder)
        node = bag.container()
        d = dir(node)
        assert 'label' in d or 'attr' in d


class TestComponentProxyDir:
    """Tests for ComponentProxy.__dir__."""

    def test_proxy_dir_with_slots(self):
        bag = BuilderBag(builder=_TestBuilder)
        proxy = bag.slotted_comp()
        assert isinstance(proxy, ComponentProxy)
        d = dir(proxy)
        assert 'left' in d
        assert 'right' in d

    def test_proxy_dir_without_slots_delegates_to_root(self):
        bag = BuilderBag(builder=_TestBuilder)
        proxy = bag.closed_comp()
        assert isinstance(proxy, ComponentProxy)
        d = dir(proxy)
        assert 'container' in d
        assert 'child_a' in d

    def test_proxy_dir_open_comp_delegates_to_root(self):
        bag = BuilderBag(builder=_TestBuilder)
        proxy = bag.open_comp()
        assert isinstance(proxy, ComponentProxy)
        d = dir(proxy)
        assert 'container' in d
