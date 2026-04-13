# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for LiveProxy, SourceProxy, DataProxy — integrated with real server."""
from __future__ import annotations

import pytest

from genro_builders.contrib.live._proxy import LiveProxy


class TestLiveProxyBasics:
    """Tests for LiveProxy top-level operations."""

    def test_builders(self, live_proxy):
        """builders() returns registered builder names."""
        result = live_proxy.builders()
        assert result == ["page"]

    def test_quit(self, live_proxy, live_server):
        """quit() sends quit command."""
        result = live_proxy.quit()
        assert result == "quitting"

    def test_wrong_token(self, live_server):
        """Connection with wrong token raises RuntimeError."""
        proxy = LiveProxy(host="localhost", port=live_server.port, token="wrong")
        with pytest.raises(RuntimeError, match="invalid token"):
            proxy.builders()


class TestSourceProxy:
    """Tests for SourceProxy operations via real server."""

    def test_keys(self, live_proxy):
        """source.keys() returns source element keys."""
        source = live_proxy.source("page")
        keys = source.keys()
        assert isinstance(keys, list)
        assert len(keys) >= 2

    def test_call_method(self, live_proxy):
        """source.heading() adds an element to the source."""
        source = live_proxy.source("page")
        keys_before = len(source.keys())
        source.heading("Remote Title")
        keys_after = len(source.keys())
        assert keys_after == keys_before + 1

    def test_getattr_private_raises(self, live_proxy):
        """Accessing private attributes raises AttributeError."""
        source = live_proxy.source("page")
        with pytest.raises(AttributeError):
            source._private

    def test_unknown_builder(self, live_proxy):
        """Accessing unknown builder raises RuntimeError."""
        source = live_proxy.source("nonexistent")
        with pytest.raises(RuntimeError, match="not found"):
            source.keys()


class TestDataProxy:
    """Tests for DataProxy operations via real server."""

    def test_getitem(self, live_proxy):
        """data[key] reads from reactive_store."""
        assert live_proxy.data["title"] == "Hello"
        assert live_proxy.data["count"] == 42

    def test_setitem(self, live_proxy, simple_app):
        """data[key] = value writes to reactive_store."""
        live_proxy.data["new_key"] = "new_value"
        assert simple_app.reactive_store["new_key"] == "new_value"

    def test_delitem(self, live_proxy, simple_app):
        """del data[key] removes from reactive_store."""
        live_proxy.data["temp"] = "to_delete"
        assert simple_app.reactive_store["temp"] == "to_delete"
        del live_proxy.data["temp"]
        assert "temp" not in list(simple_app.reactive_store.keys())

    def test_keys(self, live_proxy):
        """data.keys() lists reactive_store keys."""
        keys = live_proxy.data.keys()
        assert "title" in keys
        assert "count" in keys


class TestEndToEnd:
    """Full round-trip integration tests."""

    def test_source_manipulation_visible_on_manager(self, live_proxy, simple_app):
        """Elements added via proxy are visible on the manager's builder."""
        source = live_proxy.source("page")
        source.heading("E2E Title")
        source_keys = list(simple_app.page.source.keys())
        assert len(source_keys) >= 3

    def test_data_manipulation_visible_on_manager(self, live_proxy, simple_app):
        """Data set via proxy is visible on the manager's reactive_store."""
        live_proxy.data["e2e_key"] = "e2e_value"
        assert simple_app.reactive_store["e2e_key"] == "e2e_value"
