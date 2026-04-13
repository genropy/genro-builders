# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for LiveSession and LiveServer."""
from __future__ import annotations

import pickle
import socket

import pytest

from genro_builders.contrib.live._server import LiveServer, LiveSession, _FrameProtocol


class TestLiveSessionDispatch:
    """Tests for LiveSession.handle_command."""

    def test_builders_list(self, live_session):
        """__builders__ returns registered builder names."""
        result = live_session.handle_command(("__builders__",))
        assert result == ["page"]

    def test_source_call(self, live_session):
        """source.__call__ invokes a method on the builder's source."""
        live_session.handle_command(
            ("source.__call__", "page", "heading", ("New Title",), {})
        )
        keys = live_session.handle_command(("source.__keys__", "page"))
        assert len(keys) >= 3  # heading(^title) + text(body) + heading(New Title)

    def test_source_keys(self, live_session):
        """source.__keys__ returns source keys."""
        keys = live_session.handle_command(("source.__keys__", "page"))
        assert isinstance(keys, list)
        assert len(keys) >= 2

    def test_data_getitem(self, live_session):
        """data.__getitem__ reads from reactive_store."""
        result = live_session.handle_command(("data.__getitem__", "title"))
        assert result == "Hello"

    def test_data_setitem(self, live_session):
        """data.__setitem__ writes to reactive_store."""
        live_session.handle_command(("data.__setitem__", "new_key", "new_value"))
        result = live_session.handle_command(("data.__getitem__", "new_key"))
        assert result == "new_value"

    def test_data_keys(self, live_session):
        """data.__keys__ lists reactive_store keys."""
        keys = live_session.handle_command(("data.__keys__",))
        assert "title" in keys
        assert "count" in keys

    def test_data_delitem(self, live_session):
        """data.__delitem__ removes from reactive_store."""
        live_session.handle_command(("data.__setitem__", "temp", "value"))
        live_session.handle_command(("data.__delitem__", "temp"))
        keys = live_session.handle_command(("data.__keys__",))
        assert "temp" not in keys

    def test_quit(self, live_session):
        """__quit__ returns 'quitting'."""
        result = live_session.handle_command(("__quit__",))
        assert result == "quitting"

    def test_quit_callback(self, live_session):
        """__quit__ calls the quit callback if set."""
        called = []
        live_session._quit_callback = lambda: called.append(True)
        live_session.handle_command(("__quit__",))
        assert called == [True]

    def test_unknown_command(self, live_session):
        """Unknown command raises ValueError."""
        with pytest.raises(ValueError, match="Unknown command"):
            live_session.handle_command(("nonexistent",))

    def test_unknown_builder(self, live_session):
        """Referencing unknown builder raises ValueError."""
        with pytest.raises(ValueError, match="not found"):
            live_session.handle_command(("source.__keys__", "nonexistent"))

    def test_safe_call_default(self, live_session):
        """Default safe_call executes directly."""
        result = live_session.safe_call(lambda: 42)
        assert result == 42

    def test_safe_call_override(self, simple_app):
        """safe_call can be overridden in subclass."""
        calls = []

        class TrackedSession(LiveSession):
            def safe_call(self, func):
                calls.append("tracked")
                return func()

        session = TrackedSession(simple_app)
        session.handle_command(("data.__setitem__", "x", 1))
        assert "tracked" in calls


class TestLiveServer:
    """Tests for LiveServer lifecycle and connection handling."""

    def test_start_stop(self, live_session):
        """Server starts on a free port and stops cleanly."""
        server = LiveServer(live_session, port=0)
        server.start()
        assert server.port > 0
        assert server.token
        server.stop()

    def test_valid_command(self, live_server, live_session):
        """Server handles a valid command and returns ok."""
        proto = _FrameProtocol()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect(("127.0.0.1", live_server.port))
            msg = pickle.dumps((live_server.token, ("__builders__",)))
            proto.send(sock, msg)
            raw = proto.recv(sock)
            status, result = pickle.loads(raw)
            assert status == "ok"
            assert result == ["page"]
        finally:
            sock.close()

    def test_invalid_token(self, live_server):
        """Server rejects invalid token."""
        proto = _FrameProtocol()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect(("127.0.0.1", live_server.port))
            msg = pickle.dumps(("wrong_token", ("__builders__",)))
            proto.send(sock, msg)
            raw = proto.recv(sock)
            status, result = pickle.loads(raw)
            assert status == "error"
            assert "invalid token" in result
        finally:
            sock.close()

    def test_malformed_message(self, live_server):
        """Server handles malformed messages gracefully."""
        proto = _FrameProtocol()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect(("127.0.0.1", live_server.port))
            proto.send(sock, b"not valid pickle")
            raw = proto.recv(sock)
            status, result = pickle.loads(raw)
            assert status == "error"
        finally:
            sock.close()

    def test_multiple_connections(self, live_server):
        """Server handles multiple sequential connections."""
        proto = _FrameProtocol()
        for _ in range(3):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.connect(("127.0.0.1", live_server.port))
                msg = pickle.dumps((live_server.token, ("data.__getitem__", "title")))
                proto.send(sock, msg)
                raw = proto.recv(sock)
                status, result = pickle.loads(raw)
                assert status == "ok"
                assert result == "Hello"
            finally:
                sock.close()
