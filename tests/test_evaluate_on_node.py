# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for BuilderBagNode.evaluate_on_node — isolated 2-pass resolution."""
from __future__ import annotations

from genro_bag import Bag

from genro_builders.builder import BagBuilderBase, element
from genro_builders.builder_bag import BuilderBag


class MinimalBuilder(BagBuilderBase):
    """Minimal builder for testing node resolution."""

    @element()
    def item(self): ...


def make_node(data=None, datapath=None, **attrs):
    """Create a BuilderBagNode with given attributes and optional datapath."""
    bag = BuilderBag(builder=MinimalBuilder)
    if datapath:
        bag._parent_node = type('FakeNode', (), {'attr': {'datapath': datapath}, '_parent_bag': None})()
    node = bag.set_item("test_0", attrs.pop("node_value", None), _attributes=attrs, node_tag="item")
    return node, data or Bag()


class TestCurrentFromDatasource:
    """Tests for single-value resolution."""

    def test_pointer_absolute(self):
        data = Bag()
        data["color"] = "red"
        node, _ = make_node()
        assert node.current_from_datasource("^color", data) == "red"

    def test_pointer_relative(self):
        data = Bag()
        data.set_item("people", Bag())
        data["people"].set_item("r0", None, nome="Mario")
        bag = BuilderBag(builder=MinimalBuilder)
        root = bag.set_item("container", BuilderBag(builder=MinimalBuilder),
                            _attributes={"datapath": "people.r0"})
        inner = root.value.set_item("field_0", None,
                                     _attributes={"value": "^.?nome"},
                                     node_tag="item")
        assert inner.current_from_datasource("^.?nome", data) == "Mario"

    def test_pointer_missing(self):
        data = Bag()
        node, _ = make_node()
        assert node.current_from_datasource("^nonexistent", data) is None

    def test_plain_value(self):
        node, data = make_node()
        assert node.current_from_datasource("hello", data) == "hello"
        assert node.current_from_datasource(42, data) == 42

    def test_callable_not_resolved(self):
        """Callables are returned as-is by current_from_datasource."""
        func = lambda: "test"
        node, data = make_node()
        assert node.current_from_datasource(func, data) is func


class TestEvaluateOnNodeBasic:
    """Tests for the 2-pass evaluate_on_node."""

    def test_plain_attrs(self):
        node, data = make_node(x="10", y="20")
        result = node.evaluate_on_node(data)
        assert result["attrs"]["x"] == "10"
        assert result["attrs"]["y"] == "20"

    def test_pointer_attrs(self):
        data = Bag()
        data["title"] = "Hello"
        data["subtitle"] = "World"
        bag = BuilderBag(builder=MinimalBuilder)
        node = bag.set_item("n_0", None,
                            _attributes={"a": "^title", "b": "^subtitle"},
                            node_tag="item")
        result = node.evaluate_on_node(data)
        assert result["attrs"]["a"] == "Hello"
        assert result["attrs"]["b"] == "World"

    def test_pointer_value(self):
        data = Bag()
        data["msg"] = "ciao"
        bag = BuilderBag(builder=MinimalBuilder)
        node = bag.set_item("n_0", "^msg", node_tag="item")
        result = node.evaluate_on_node(data)
        assert result["node_value"] == "ciao"

    def test_plain_value(self):
        bag = BuilderBag(builder=MinimalBuilder)
        node = bag.set_item("n_0", "static text", node_tag="item")
        result = node.evaluate_on_node(Bag())
        assert result["node_value"] == "static text"

    def test_node_reference(self):
        node, data = make_node(x="1")
        result = node.evaluate_on_node(data)
        assert result["node"] is node


class TestEvaluateOnNodeCallables:
    """Tests for pass-2 callable resolution."""

    def test_callable_receives_resolved_attrs(self):
        """Callable gets resolved attrs matched by parameter name."""
        data = Bag()
        data["first"] = "Mario"
        data["last"] = "Rossi"
        bag = BuilderBag(builder=MinimalBuilder)
        node = bag.set_item("n_0", None,
                            _attributes={
                                "first": "^first",
                                "last": "^last",
                                "label": lambda first, last: f"{last} {first}",
                            },
                            node_tag="item")
        result = node.evaluate_on_node(data)
        assert result["attrs"]["first"] == "Mario"
        assert result["attrs"]["last"] == "Rossi"
        assert result["attrs"]["label"] == "Rossi Mario"

    def test_callable_with_plain_attrs(self):
        """Callable works with non-pointer resolved attrs."""
        bag = BuilderBag(builder=MinimalBuilder)
        node = bag.set_item("n_0", None,
                            _attributes={
                                "a": 10,
                                "b": 20,
                                "total": lambda a, b: a + b,
                            },
                            node_tag="item")
        result = node.evaluate_on_node(Bag())
        assert result["attrs"]["total"] == 30

    def test_callable_with_kwargs(self):
        """Callable with **kwargs receives all non-private resolved attrs."""
        bag = BuilderBag(builder=MinimalBuilder)
        node = bag.set_item("n_0", None,
                            _attributes={
                                "x": 1,
                                "y": 2,
                                "_tag": "item",
                                "summary": lambda **kw: sum(kw.values()),
                            },
                            node_tag="item")
        result = node.evaluate_on_node(Bag())
        assert result["attrs"]["summary"] == 3  # x + y, _tag excluded

    def test_callable_ignores_missing_params(self):
        """Callable only gets params that exist in resolved attrs."""
        bag = BuilderBag(builder=MinimalBuilder)
        node = bag.set_item("n_0", None,
                            _attributes={
                                "a": 10,
                                "compute": lambda a, b=0: a + b,
                            },
                            node_tag="item")
        result = node.evaluate_on_node(Bag())
        assert result["attrs"]["compute"] == 10  # a=10, b not in attrs

    def test_callable_partial_match(self):
        """Only matching parameter names are passed."""
        bag = BuilderBag(builder=MinimalBuilder)
        node = bag.set_item("n_0", None,
                            _attributes={
                                "width": 100,
                                "height": 50,
                                "color": "red",
                                "area": lambda width, height: width * height,
                            },
                            node_tag="item")
        result = node.evaluate_on_node(Bag())
        assert result["attrs"]["area"] == 5000
        assert result["attrs"]["color"] == "red"

    def test_data_formula_pattern(self):
        """func + separate kwargs: same pattern as data_formula."""
        bag = BuilderBag(builder=MinimalBuilder)
        node = bag.set_item("n_0", None,
                            _attributes={
                                "func": lambda a, b: a + b,
                                "a": 10,
                                "b": 20,
                            },
                            node_tag="item")
        result = node.evaluate_on_node(Bag())
        assert result["attrs"]["func"] == 30

    def test_mixed_pointers_and_callable(self):
        """Pointers resolved first, then callable uses them."""
        data = Bag()
        data["price"] = 100
        bag = BuilderBag(builder=MinimalBuilder)
        node = bag.set_item("n_0", None,
                            _attributes={
                                "price": "^price",
                                "qty": 3,
                                "total": lambda price, qty: price * qty,
                            },
                            node_tag="item")
        result = node.evaluate_on_node(data)
        assert result["attrs"]["price"] == 100
        assert result["attrs"]["qty"] == 3
        assert result["attrs"]["total"] == 300


    def test_callable_with_pointer_defaults(self):
        """Callable with ^pointer defaults resolves from data store."""
        data = Bag()
        data["selected"] = True
        bag = BuilderBag(builder=MinimalBuilder)
        node = bag.set_item("n_0", None,
                            _attributes={
                                "color": lambda selected='^selected': 'red' if selected else 'blue',
                            },
                            node_tag="item")
        result = node.evaluate_on_node(data)
        assert result["attrs"]["color"] == "red"

    def test_callable_with_multiple_pointer_defaults(self):
        """Multiple ^pointer defaults resolved from data store."""
        data = Bag()
        data["name"] = "Alice"
        data["role"] = "Admin"
        bag = BuilderBag(builder=MinimalBuilder)
        node = bag.set_item("n_0", None,
                            _attributes={
                                "label": lambda name='^name', role='^role': f'{name} ({role})',
                            },
                            node_tag="item")
        result = node.evaluate_on_node(data)
        assert result["attrs"]["label"] == "Alice (Admin)"


class TestGetAttributeFromDatasource:
    """Tests for single-attribute resolution."""

    def test_resolves_pointer(self):
        data = Bag()
        data["color"] = "blue"
        bag = BuilderBag(builder=MinimalBuilder)
        node = bag.set_item("n_0", None,
                            _attributes={"fill": "^color"},
                            node_tag="item")
        assert node.get_attribute_from_datasource("fill", data) == "blue"

    def test_returns_plain(self):
        bag = BuilderBag(builder=MinimalBuilder)
        node = bag.set_item("n_0", None,
                            _attributes={"fill": "red"},
                            node_tag="item")
        assert node.get_attribute_from_datasource("fill", Bag()) == "red"

    def test_missing_attr(self):
        bag = BuilderBag(builder=MinimalBuilder)
        node = bag.set_item("n_0", None, node_tag="item")
        assert node.get_attribute_from_datasource("nonexistent", Bag()) is None
