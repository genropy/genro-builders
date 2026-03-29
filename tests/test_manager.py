# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for BuilderManager — multi-builder coordination with shared data."""
from __future__ import annotations

from genro_bag import Bag

from genro_builders.manager import BuilderManager

from .helpers import TestBuilder


class TestManagerBasics:
    """Tests for basic BuilderManager operations."""

    def test_register_builder(self):
        """register_builder creates and returns a builder."""
        mgr = BuilderManager()
        builder = mgr.register_builder("page", TestBuilder)
        assert builder is not None
        assert mgr.get_builder("page") is builder

    def test_builder_receives_manager(self):
        """Registered builder has _manager set to the manager."""
        mgr = BuilderManager()
        builder = mgr.register_builder("page", TestBuilder)
        assert builder._manager is mgr

    def test_builder_data_proxied_to_manager(self):
        """Builder.data returns the manager's shared data."""
        mgr = BuilderManager()
        builder = mgr.register_builder("page", TestBuilder)
        assert builder.data is mgr.data

    def test_manager_data_is_backref_enabled(self):
        """Manager's data Bag has backref enabled."""
        mgr = BuilderManager()
        assert mgr.data.backref is True


class TestManagerMultipleBuilders:
    """Tests for multiple builders sharing data."""

    def test_multiple_builders_share_data(self):
        """Two registered builders share the same data."""
        mgr = BuilderManager()
        b1 = mgr.register_builder("page", TestBuilder)
        b2 = mgr.register_builder("sidebar", TestBuilder)
        assert b1.data is b2.data
        assert b1.data is mgr.data

    def test_data_replacement_propagates(self):
        """Replacing manager.data updates all builders."""
        mgr = BuilderManager()
        b1 = mgr.register_builder("page", TestBuilder)
        b2 = mgr.register_builder("sidebar", TestBuilder)

        new_data = Bag()
        new_data["key"] = "value"
        mgr.data = new_data

        assert b1.data is mgr.data
        assert b2.data is mgr.data
        assert b1.data["key"] == "value"

    def test_data_setter_accepts_dict(self):
        """Manager.data setter converts dict to Bag."""
        mgr = BuilderManager()
        mgr.data = {"name": "test"}
        assert isinstance(mgr.data, Bag)
        assert mgr.data["name"] == "test"


class TestManagerHook:
    """Tests for on_builder_changed hook."""

    def test_on_builder_changed_is_callable(self):
        """Default on_builder_changed does nothing (no error)."""
        mgr = BuilderManager()
        builder = mgr.register_builder("page", TestBuilder)
        mgr.on_builder_changed(builder, "compiled")

    def test_on_builder_changed_override(self):
        """Subclass can override on_builder_changed."""
        events = []

        class MyManager(BuilderManager):
            def on_builder_changed(self, builder, event):
                events.append((builder, event))

        mgr = MyManager()
        builder = mgr.register_builder("page", TestBuilder)
        mgr.on_builder_changed(builder, "test_event")

        assert len(events) == 1
        assert events[0][1] == "test_event"


class TestManagerAutonomousBuilder:
    """Tests for autonomous builder created via manager."""

    def test_autonomous_builder_has_source(self):
        """Builder created via manager has source property."""
        mgr = BuilderManager()
        builder = mgr.register_builder("page", TestBuilder)
        assert builder.source is not None

    def test_autonomous_builder_has_compiled(self):
        """Builder created via manager has compiled property."""
        mgr = BuilderManager()
        builder = mgr.register_builder("page", TestBuilder)
        assert builder.compiled is not None

    def test_autonomous_builder_source_is_builder_bag(self):
        """Source bag has the builder attached."""
        mgr = BuilderManager()
        builder = mgr.register_builder("page", TestBuilder)
        assert builder.source.builder is not None

    def test_builder_source_accepts_elements(self):
        """Can populate source with builder elements."""
        mgr = BuilderManager()
        builder = mgr.register_builder("page", TestBuilder)
        builder.source.heading("Hello")
        assert len(builder.source) == 1


class TestStandaloneAutonomousBuilder:
    """Tests for autonomous builder without manager."""

    def test_standalone_builder(self):
        """Builder without bag or manager enters autonomous mode."""
        builder = TestBuilder()
        assert builder.source is not None
        assert builder.compiled is not None
        assert builder.data is not None

    def test_standalone_data_is_own(self):
        """Standalone builder has its own data, not proxied."""
        builder = TestBuilder()
        builder.data["key"] = "value"
        assert builder.data["key"] == "value"

    def test_standalone_source_accepts_elements(self):
        """Standalone builder source accepts elements."""
        builder = TestBuilder()
        builder.source.heading("Hello")
        assert len(builder.source) == 1

    def test_standalone_data_replacement(self):
        """Standalone builder data setter works."""
        builder = TestBuilder()
        new_data = Bag()
        new_data["name"] = "Alice"
        builder.data = new_data
        assert builder.data["name"] == "Alice"

    def test_standalone_data_from_dict(self):
        """Standalone builder data setter converts dict."""
        builder = TestBuilder()
        builder.data = {"name": "Bob"}
        assert isinstance(builder.data, Bag)
        assert builder.data["name"] == "Bob"
