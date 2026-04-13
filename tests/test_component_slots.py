# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for named slots in @component."""
from __future__ import annotations

from genro_builders.builder import BagBuilderBase, component, element
from genro_builders.builder_bag import BuilderBag
from genro_builders.builder._component import ComponentProxy


class TestComponentProxy:
    """Tests for ComponentProxy behavior."""

    def test_proxy_delegates_to_root(self):
        """Proxy delegates attribute access to root bag."""

        class Builder(BagBuilderBase):
            @component(sub_tags="")
            def panel(self, comp, **kwargs):
                return comp

            @element()
            def item(self): ...

        bag = BuilderBag(builder=Builder)
        proxy = bag.panel()

        assert isinstance(proxy, ComponentProxy)
        # Delegation: calling item() on proxy adds to bag
        proxy.item("hello")
        assert len(bag) == 2  # panel + item

    def test_proxy_getitem(self):
        """Proxy delegates __getitem__ to root."""

        class Builder(BagBuilderBase):
            @component(sub_tags="")
            def panel(self, comp, **kwargs):
                return comp

            @element()
            def item(self): ...

        bag = BuilderBag(builder=Builder)
        proxy = bag.panel()
        proxy.item("hello")
        assert bag["item_0"] == "hello"

    def test_proxy_len(self):
        """Proxy delegates __len__ to root."""

        class Builder(BagBuilderBase):
            @component(sub_tags="")
            def panel(self, comp, **kwargs):
                return comp

        bag = BuilderBag(builder=Builder)
        proxy = bag.panel()
        assert len(proxy) == 1  # panel node

    def test_proxy_iter(self):
        """Proxy delegates __iter__ to root."""

        class Builder(BagBuilderBase):
            @component(sub_tags="")
            def panel(self, comp, **kwargs):
                return comp

            @element()
            def item(self): ...

        bag = BuilderBag(builder=Builder)
        proxy = bag.panel()
        proxy.item("a")
        proxy.item("b")
        tags = [n.node_tag for n in proxy]
        assert tags == ["panel", "item", "item"]

    def test_proxy_repr_no_slots(self):
        """Proxy repr without slots."""

        class Builder(BagBuilderBase):
            @component(sub_tags="")
            def panel(self, comp, **kwargs):
                return comp

        bag = BuilderBag(builder=Builder)
        proxy = bag.panel()
        r = repr(proxy)
        assert "ComponentProxy" in r
        assert "slots" not in r


class TestSlotDeclaration:
    """Tests for @component(slots=[...]) declaration."""

    def test_slots_stored_in_schema(self):
        """Slots list is stored in class schema."""

        class Builder(BagBuilderBase):
            @component(slots=["left", "right"])
            def panel(self, comp, **kwargs):
                return comp

            @element()
            def item(self): ...

        info = Builder._class_schema.get_node("panel").attr
        assert info["slots"] == ["left", "right"]

    def test_slots_none_when_absent(self):
        """No slots attribute when not declared."""

        class Builder(BagBuilderBase):
            @component(sub_tags="")
            def panel(self, comp, **kwargs):
                return comp

        info = Builder._class_schema.get_node("panel").attr
        assert info.get("slots") is None

    def test_proxy_has_slot_attributes(self):
        """Proxy exposes slot Bags as attributes."""

        class Builder(BagBuilderBase):
            @component(slots=["left", "right"])
            def panel(self, comp, **kwargs):
                return comp

            @element()
            def item(self): ...

        bag = BuilderBag(builder=Builder)
        proxy = bag.panel()

        assert isinstance(proxy, ComponentProxy)
        # Slots are accessible as attributes
        assert proxy.left is not None
        assert proxy.right is not None
        # Slots are BuilderBag instances
        assert hasattr(proxy.left, "builder")
        assert hasattr(proxy.right, "builder")

    def test_proxy_repr_with_slots(self):
        """Proxy repr with slots."""

        class Builder(BagBuilderBase):
            @component(slots=["left", "right"])
            def panel(self, comp, **kwargs):
                return comp

        bag = BuilderBag(builder=Builder)
        proxy = bag.panel()
        r = repr(proxy)
        assert "ComponentProxy" in r
        assert "left" in r
        assert "right" in r


class TestSlotPopulation:
    """Tests for populating slots at recipe time."""

    def test_populate_slot_at_recipe_time(self):
        """User can add elements to slot Bags via proxy."""

        class Builder(BagBuilderBase):
            @component(slots=["content"])
            def panel(self, comp, **kwargs):
                return comp

            @element()
            def item(self): ...

        bag = BuilderBag(builder=Builder)
        proxy = bag.panel()
        proxy.content.item("hello")
        proxy.content.item("world")

        # Slot bag has 2 items
        assert len(proxy.content) == 2

    def test_slot_and_root_independent(self):
        """Slot population doesn't affect root bag."""

        class Builder(BagBuilderBase):
            @component(slots=["sidebar"])
            def layout(self, comp, **kwargs):
                return comp

            @element()
            def item(self): ...

        bag = BuilderBag(builder=Builder)
        proxy = bag.layout()
        proxy.sidebar.item("nav1")
        proxy.item("main content")

        # Root has layout + item
        assert len(bag) == 2
        # Sidebar has 1 item
        assert len(proxy.sidebar) == 1

    def test_empty_slot_at_compile(self):
        """Slot declared but not populated by user — no error."""

        class Builder(BagBuilderBase):
            @component(slots=["left", "right"])
            def panel(self, comp, **kwargs):
                comp.item("header")
                left_pane = comp.item("left_zone")
                right_pane = comp.item("right_zone")
                return {"left": left_pane, "right": right_pane}

            @element()
            def item(self): ...

        bag = BuilderBag(builder=Builder)
        bag.panel()
        # Don't populate any slot — should not error
        node = bag.get_node("panel_0")
        expanded = node.get_value(static=False)
        assert expanded is not None


class TestSlotMounting:
    """Tests for slot content being mounted at compile time."""

    def test_slot_content_mounted_into_dest(self):
        """At compile time, slot content is copied into destination Bags."""

        class Builder(BagBuilderBase):
            @component(slots=["content"])
            def panel(self, comp, **kwargs):
                comp.header("Panel Title")
                body = comp.container()
                return {"content": body}

            @element()
            def header(self): ...

            @element(sub_tags="*")
            def container(self): ...

            @element()
            def item(self): ...

        bag = BuilderBag(builder=Builder)
        proxy = bag.panel()
        proxy.content.item("Item 1")
        proxy.content.item("Item 2")

        # Trigger lazy expansion
        node = bag.get_node("panel_0")
        expanded = node.get_value(static=False)

        # The expanded bag should have: header + container
        assert len(expanded) == 2
        # The container should have the 2 items from the slot
        container_node = expanded.get_node("container_0")
        assert len(container_node.value) == 2
        assert container_node.value["item_0"] == "Item 1"
        assert container_node.value["item_1"] == "Item 2"

    def test_multiple_slots_mounted(self):
        """Multiple slots are mounted into their respective destinations."""

        class Builder(BagBuilderBase):
            @component(slots=["left", "right"])
            def split(self, comp, **kwargs):
                left_pane = comp.container()
                right_pane = comp.container()
                return {"left": left_pane, "right": right_pane}

            @element(sub_tags="*")
            def container(self): ...

            @element()
            def item(self): ...

        bag = BuilderBag(builder=Builder)
        proxy = bag.split()
        proxy.left.item("L1")
        proxy.left.item("L2")
        proxy.right.item("R1")

        # Trigger expansion
        node = bag.get_node("split_0")
        expanded = node.get_value(static=False)

        left_container = expanded.get_node("container_0")
        right_container = expanded.get_node("container_1")
        assert len(left_container.value) == 2
        assert len(right_container.value) == 1
        assert left_container.value["item_0"] == "L1"
        assert right_container.value["item_0"] == "R1"

    def test_slot_preserves_attributes(self):
        """Slot content preserves node attributes during mounting."""

        class Builder(BagBuilderBase):
            @component(slots=["content"])
            def panel(self, comp, **kwargs):
                body = comp.container()
                return {"content": body}

            @element(sub_tags="*")
            def container(self): ...

            @element()
            def item(self): ...

        bag = BuilderBag(builder=Builder)
        proxy = bag.panel()
        proxy.content.item("styled", color="red", size=42)

        node = bag.get_node("panel_0")
        expanded = node.get_value(static=False)
        container = expanded.get_node("container_0")
        item_node = container.value.get_node("item_0")
        assert item_node.attr["color"] == "red"
        assert item_node.attr["size"] == 42

    def test_slot_preserves_tags(self):
        """Slot content preserves node tags during mounting."""

        class Builder(BagBuilderBase):
            @component(slots=["content"])
            def panel(self, comp, **kwargs):
                body = comp.container()
                return {"content": body}

            @element(sub_tags="*")
            def container(self): ...

            @element()
            def header(self): ...

            @element()
            def footer(self): ...

        bag = BuilderBag(builder=Builder)
        proxy = bag.panel()
        proxy.content.header("Title")
        proxy.content.footer("End")

        node = bag.get_node("panel_0")
        expanded = node.get_value(static=False)
        container = expanded.get_node("container_0")
        tags = [n.node_tag for n in container.value]
        assert tags == ["header", "footer"]


class TestSlotWithChaining:
    """Tests for chaining behavior with slots."""

    def test_chaining_via_proxy_root(self):
        """Root delegation allows chaining after component with slots."""

        class Builder(BagBuilderBase):
            @component(slots=["content"])
            def panel(self, comp, **kwargs):
                return comp

            @element()
            def item(self): ...

        bag = BuilderBag(builder=Builder)
        proxy = bag.panel()
        # Chain on root via proxy
        proxy.item("after panel")

        assert len(bag) == 2  # panel + item

    def test_no_slot_component_backward_compat(self):
        """Component without slots: proxy is fully transparent."""

        class Builder(BagBuilderBase):
            @component(sub_tags="")
            def widget(self, comp, **kwargs):
                comp.inner("built")
                return comp

            @element()
            def inner(self): ...

            @element()
            def outer(self): ...

        bag = BuilderBag(builder=Builder)
        proxy = bag.widget()
        proxy.outer("after widget")

        assert len(bag) == 2  # widget + outer
        assert isinstance(proxy, ComponentProxy)
