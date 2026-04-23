# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for LiveRegistry — file-based session registry."""
from __future__ import annotations

import threading

import pytest


class TestLiveRegistry:
    """Tests for LiveRegistry CRUD operations."""

    def test_register_and_get(self, tmp_registry):
        """register + get_info round-trip."""
        tmp_registry.register("myapp", 9999, "token123", pid=1234)
        info = tmp_registry.get_info("myapp")
        assert info is not None
        assert info["port"] == 9999
        assert info["token"] == "token123"
        assert info["pid"] == 1234

    def test_unregister(self, tmp_registry):
        """unregister removes the entry."""
        tmp_registry.register("myapp", 9999, "token123")
        tmp_registry.unregister("myapp")
        assert tmp_registry.get_info("myapp") is None

    def test_unregister_nonexistent(self, tmp_registry):
        """unregister on non-existent name does not raise."""
        tmp_registry.unregister("nonexistent")

    def test_list_all(self, tmp_registry):
        """list_all returns all entries."""
        tmp_registry.register("app1", 9001, "t1")
        tmp_registry.register("app2", 9002, "t2")
        all_apps = tmp_registry.list_all()
        assert "app1" in all_apps
        assert "app2" in all_apps
        assert all_apps["app1"]["port"] == 9001

    def test_get_info_nonexistent(self, tmp_registry):
        """get_info returns None for unknown name."""
        assert tmp_registry.get_info("unknown") is None

    def test_find_free_port(self, tmp_registry):
        """find_free_port returns a usable port number."""
        port = tmp_registry.find_free_port()
        assert isinstance(port, int)
        assert port > 0

    def test_overwrite_entry(self, tmp_registry):
        """Registering same name overwrites the entry."""
        tmp_registry.register("myapp", 9001, "old_token")
        tmp_registry.register("myapp", 9002, "new_token")
        info = tmp_registry.get_info("myapp")
        assert info["port"] == 9002
        assert info["token"] == "new_token"

    def test_concurrent_writes(self, tmp_registry):
        """Multiple threads can write without corruption."""
        errors = []

        def register_app(name, port):
            try:
                tmp_registry.register(name, port, f"token_{name}")
            except Exception as exc:
                errors.append(exc)

        threads = [
            threading.Thread(target=register_app, args=(f"app{i}", 9000 + i))
            for i in range(10)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        all_apps = tmp_registry.list_all()
        assert len(all_apps) == 10

    def test_empty_registry_file(self, tmp_registry):
        """list_all returns empty dict when registry file doesn't exist."""
        assert tmp_registry.list_all() == {}

    def test_corrupted_registry_file(self, tmp_registry):
        """Corrupted JSON file is handled gracefully."""
        tmp_registry._ensure_dir()
        tmp_registry._registry_file.write_text("not json", encoding="utf-8")
        assert tmp_registry.list_all() == {}
