# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Shared fixtures for contrib/live tests."""
from __future__ import annotations

import pytest

from genro_builders.contrib.live._registry import LiveRegistry
from genro_builders.contrib.live._server import LiveServer, LiveSession
from genro_builders.manager import BuilderManager, ReactiveManager

from ..helpers import TestBuilder


class SimpleApp(BuilderManager):
    """Single-builder app for testing."""

    def on_init(self):
        self.page = self.register_builder("page", TestBuilder)

    def store(self, data):
        data["title"] = "Hello"
        data["count"] = 42

    def main(self, source):
        source.heading(value="^title")
        source.text(value="body text")


class MultiApp(BuilderManager):
    """Multi-builder app for testing."""

    def on_init(self):
        self.page = self.register_builder("page", TestBuilder)
        self.sidebar = self.register_builder("sidebar", TestBuilder)

    def store(self, data):
        data["title"] = "Multi"

    def main_page(self, source):
        source.heading(value="^title")

    def main_sidebar(self, source):
        source.item(value="nav")


@pytest.fixture()
def simple_app():
    """A single-builder BuilderManager with data populated."""
    app = SimpleApp()
    app.setup()
    app.build()
    return app


@pytest.fixture()
def multi_app():
    """A multi-builder BuilderManager with data populated."""
    app = MultiApp()
    app.setup()
    app.build()
    return app


@pytest.fixture()
def live_session(simple_app):
    """A LiveSession wrapping the simple_app."""
    return LiveSession(simple_app)


@pytest.fixture()
def live_server(live_session):
    """A started LiveServer on a free port. Stopped on teardown."""
    server = LiveServer(live_session, port=0)
    server.start()
    yield server
    server.stop()


@pytest.fixture()
def live_proxy(live_server):
    """A LiveProxy connected to the live_server."""
    from genro_builders.contrib.live._proxy import LiveProxy

    return LiveProxy(host="localhost", port=live_server.port, token=live_server.token)


@pytest.fixture()
def tmp_registry(tmp_path, monkeypatch):
    """A LiveRegistry using a temporary directory."""
    registry = LiveRegistry()
    monkeypatch.setattr(registry, "_registry_dir", tmp_path)
    monkeypatch.setattr(registry, "_registry_file", tmp_path / "registry.json")
    monkeypatch.setattr(registry, "_lock_file", tmp_path / ".lock")
    return registry
