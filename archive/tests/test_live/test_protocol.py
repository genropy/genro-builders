# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for _FrameProtocol — wire-level framing."""
from __future__ import annotations

import pickle
import socket

import pytest

from genro_builders.contrib.live._server import _FrameProtocol


class TestFrameProtocol:
    """Tests for length-prefixed framing."""

    def _socket_pair(self) -> tuple[socket.socket, socket.socket]:
        """Create a connected pair of TCP sockets via loopback."""
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("127.0.0.1", 0))
        srv.listen(1)
        port = srv.getsockname()[1]

        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(("127.0.0.1", port))
        server_conn, _ = srv.accept()
        srv.close()
        return client, server_conn

    def test_roundtrip_small(self):
        """Small message survives send + recv."""
        proto = _FrameProtocol()
        a, b = self._socket_pair()
        try:
            data = pickle.dumps({"key": "value", "n": 42})
            proto.send(a, data)
            received = proto.recv(b)
            assert received == data
            assert pickle.loads(received) == {"key": "value", "n": 42}
        finally:
            a.close()
            b.close()

    def test_roundtrip_large(self):
        """Large message (256 KB) survives send + recv via threaded send."""
        import threading

        proto = _FrameProtocol()
        a, b = self._socket_pair()
        data = b"X" * (256 * 1024)
        received = [None]

        def do_recv():
            received[0] = proto.recv(b)

        try:
            t = threading.Thread(target=do_recv)
            t.start()
            proto.send(a, data)
            t.join(timeout=5.0)
            assert received[0] == data
        finally:
            a.close()
            b.close()

    def test_recv_returns_none_on_closed_socket(self):
        """recv returns None when sender closes without sending."""
        proto = _FrameProtocol()
        a, b = self._socket_pair()
        try:
            a.close()
            result = proto.recv(b)
            assert result is None
        finally:
            b.close()

    def test_multiple_messages(self):
        """Multiple messages can be sent and received sequentially."""
        proto = _FrameProtocol()
        a, b = self._socket_pair()
        try:
            for i in range(5):
                data = pickle.dumps(f"msg-{i}")
                proto.send(a, data)
                received = proto.recv(b)
                assert pickle.loads(received) == f"msg-{i}"
        finally:
            a.close()
            b.close()

    def test_oversized_message_rejected(self):
        """Message exceeding MAX_MESSAGE_SIZE raises ValueError."""
        proto = _FrameProtocol()
        a, b = self._socket_pair()
        try:
            import struct

            fake_header = struct.pack(">I", proto.MAX_MESSAGE_SIZE + 1)
            a.sendall(fake_header)
            with pytest.raises(ValueError, match="Message too large"):
                proto.recv(b)
        finally:
            a.close()
            b.close()
