# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for ``BagResolver`` values resolved by ``runtime_values``.

A resolver SUPPLIES a value in place: the recipe declares it where the
value lives, instead of pairing a datastore entry with a ``^pointer``.
``runtime_values`` calls it wherever it sits — as the node value or in an
attribute — so a reader cannot tell a resolved value from a literal.

A resolver needs no node of its own: it is callable, and its cache and
TTL live in the resolver itself.
"""
from __future__ import annotations

import time

from genro_bag.resolver import BagSyncResolver

from genro_builders.builder import BuilderBase, element


class _Fixed(BagSyncResolver):
    """Returns a value handed at construction time."""

    class_kwargs = dict(BagSyncResolver.class_kwargs)

    def load(self):
        return self._kw.get("payload")


class _Counter(BagSyncResolver):
    """Counts its own calls, so caching is observable."""

    class_kwargs = dict(BagSyncResolver.class_kwargs)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.calls = 0

    def load(self):
        self.calls += 1
        return f"call-{self.calls}"


class _DocBuilder(BuilderBase):
    _name = "_resolvertest"
    _default_render_mode = "xml"

    @element(sub_tags="item")
    def doc(self, **kwargs): ...

    @element(parent_tags="doc")
    def item(self, **kwargs): ...


def _build(main):
    class _D(_DocBuilder):
        pass

    _D.main = lambda self, root: main(root)
    page = _D()
    page.create()
    return page


def _item(page, index=0):
    doc = next(iter(page.source)).value
    return list(doc)[index]


def test_resolver_as_node_value_is_called():
    page = _build(lambda root: root.doc().item(_Fixed(payload="hello")))
    value, _attrs = page.runtime_values(_item(page))
    assert value == "hello"


def test_resolver_in_attribute_is_called():
    page = _build(lambda root: root.doc().item(title=_Fixed(payload="hi")))
    _value, attrs = page.runtime_values(_item(page))
    assert attrs["title"] == "hi"


def test_literal_attribute_is_untouched():
    """No behaviour change for ordinary values."""
    page = _build(lambda root: root.doc().item(title="plain", n=3))
    _value, attrs = page.runtime_values(_item(page))
    assert attrs == {"title": "plain", "n": 3}


def test_resolved_attribute_reaches_the_render():
    """The point of it: the markup carries the value, not the object."""
    page = _build(lambda root: root.doc().item(title=_Fixed(payload="42")))
    assert page.render(target=False) == '<doc><item title="42"></item></doc>'


def test_resolver_cache_belongs_to_the_resolver():
    """``cache_time`` works with no node: two renders, one load."""
    counter = _Counter(cache_time=False)  # infinite cache
    page = _build(lambda root: root.doc().item(title=counter))
    first = page.render(target=False)
    second = page.render(target=False)
    assert first == second
    assert counter.calls == 1


def test_uncached_resolver_is_called_on_every_render():
    """Without cache each render asks again — the author's choice."""
    counter = _Counter()
    page = _build(lambda root: root.doc().item(title=counter))
    page.render(target=False)
    page.render(target=False)
    assert counter.calls == 2


def test_cache_time_expires():
    """A TTL measured on a resolver that has no parent node."""
    counter = _Counter(cache_time=0.3)
    page = _build(lambda root: root.doc().item(title=counter))
    page.render(target=False)
    page.render(target=False)
    assert counter.calls == 1
    time.sleep(0.4)
    page.render(target=False)
    assert counter.calls == 2
