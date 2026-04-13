# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Client proxies for remote LiveSession control.

LiveProxy connects to a running LiveServer and provides SourceProxy
(per-builder source manipulation) and DataProxy (reactive_store access).

Each command opens a new TCP connection, sends a framed pickle message,
and receives the response. This keeps the protocol stateless and avoids
connection management.

Usage:
    proxy = LiveProxy(host="localhost", port=9999, token="abc123")
    proxy.source("page").div("Hello!")
    proxy.data["title"] = "Updated"
    proxy.builders()  # -> ["page"]
"""
from __future__ import annotations

import pickle
import socket
from typing import Any

from genro_builders.contrib.live._server import _FrameProtocol


class LiveProxy:
    """Client proxy for a remote LiveSession. One socket per command."""

    def __init__(self, host: str = "localhost", port: int = 9999, token: str = "") -> None:
        self._host = host
        self._port = port
        self._token = token
        self._protocol = _FrameProtocol()

    def _send(self, cmd: tuple[Any, ...]) -> Any:
        """Open socket, send (token, cmd), receive (status, result)."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.connect((self._host, self._port))
            payload = pickle.dumps((self._token, cmd))
            self._protocol.send(sock, payload)
            raw = self._protocol.recv(sock)
            if raw is None:
                raise ConnectionError("Server closed connection without response")
            status, result = pickle.loads(raw)
            if status == "error":
                raise RuntimeError(f"Remote error: {result}")
            return result
        finally:
            sock.close()

    def source(self, builder_name: str = "") -> SourceProxy:
        """Return a SourceProxy for the named builder.

        If builder_name is empty and the manager has exactly one builder,
        the server resolves it automatically.
        """
        return SourceProxy(self, builder_name)

    @property
    def data(self) -> DataProxy:
        """Return a DataProxy for the reactive_store."""
        return DataProxy(self)

    def builders(self) -> list[str]:
        """List registered builder names on the remote session."""
        result: list[str] = self._send(("__builders__",))
        return result

    def quit(self) -> str:
        """Send quit command to the remote session."""
        result: str = self._send(("__quit__",))
        return result


class SourceProxy:
    """Proxy for a specific builder's source Bag.

    Forwards attribute access as remote __call__ commands.
    Supports keys(), __getitem__, __setitem__.
    """

    def __init__(self, live_proxy: LiveProxy, builder_name: str) -> None:
        self._live_proxy = live_proxy
        self._builder_name = builder_name

    def __getattr__(self, name: str) -> Any:
        """Forward method calls to the remote builder source."""
        if name.startswith("_"):
            raise AttributeError(name)

        def _remote_call(*args: Any, **kwargs: Any) -> Any:
            return self._live_proxy._send(
                ("source.__call__", self._builder_name, name, args, kwargs)
            )

        return _remote_call

    def keys(self) -> list[str]:
        """List keys in the builder's source."""
        result: list[str] = self._live_proxy._send(("source.__keys__", self._builder_name))
        return result

    def __getitem__(self, key: str) -> Any:
        """Get item from builder's source."""
        return self._live_proxy._send(("source.__getitem__", self._builder_name, key))

    def __setitem__(self, key: str, value: Any) -> None:
        """Set item on builder's source."""
        self._live_proxy._send(("source.__setitem__", self._builder_name, key, value))


class DataProxy:
    """Proxy for the reactive_store. Dict-like access over the wire."""

    def __init__(self, live_proxy: LiveProxy) -> None:
        self._live_proxy = live_proxy

    def __getitem__(self, key: str) -> Any:
        """Get value from reactive_store."""
        return self._live_proxy._send(("data.__getitem__", key))

    def __setitem__(self, key: str, value: Any) -> None:
        """Set value on reactive_store."""
        self._live_proxy._send(("data.__setitem__", key, value))

    def __delitem__(self, key: str) -> None:
        """Delete key from reactive_store."""
        self._live_proxy._send(("data.__delitem__", key))

    def keys(self) -> list[str]:
        """List keys in reactive_store."""
        result: list[str] = self._live_proxy._send(("data.__keys__",))
        return result
