# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""LiveSession and LiveServer — remote command execution for BuilderManager.

LiveSession wraps a BuilderManager, exposing its builders' source Bags
and the shared reactive_store for remote manipulation. Commands are
dispatched via handle_command() with structured namespaces (source.*, data.*).

LiveServer runs a TCP socket server in a daemon thread, authenticating
clients via token and delegating commands to a LiveSession.

Wire protocol: pickle with 4-byte big-endian length prefix.
Message format: client sends (token, cmd), server responds ("ok", result)
or ("error", message).
"""
from __future__ import annotations

import pickle
import secrets
import socket
import struct
import threading
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from genro_builders.contrib.live._registry import LiveRegistry

if TYPE_CHECKING:
    from genro_builders.manager import BuilderManager


class _FrameProtocol:
    """Length-prefixed framing over TCP sockets.

    Each message: 4-byte big-endian length header + pickle payload.
    Max message size: 16 MB.
    """

    HEADER_FORMAT = ">I"
    HEADER_SIZE = 4
    MAX_MESSAGE_SIZE = 16 * 1024 * 1024

    def send(self, sock: socket.socket, data: bytes) -> None:
        """Send data with 4-byte length prefix."""
        header = struct.pack(self.HEADER_FORMAT, len(data))
        sock.sendall(header + data)

    def recv(self, sock: socket.socket) -> bytes | None:
        """Receive length-prefixed data. Returns None on disconnect."""
        header = self._recv_exact(sock, self.HEADER_SIZE)
        if header is None:
            return None
        (length,) = struct.unpack(self.HEADER_FORMAT, header)
        if length > self.MAX_MESSAGE_SIZE:
            raise ValueError(f"Message too large: {length} bytes (max {self.MAX_MESSAGE_SIZE})")
        return self._recv_exact(sock, length)

    def _recv_exact(self, sock: socket.socket, n: int) -> bytes | None:
        """Receive exactly *n* bytes. Returns None on premature disconnect."""
        chunks: list[bytes] = []
        remaining = n
        while remaining > 0:
            chunk = sock.recv(min(remaining, 65536))
            if not chunk:
                return None
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)


class LiveSession:
    """Wraps a BuilderManager for remote command execution.

    Exposes source (per-builder) and data (reactive_store) for remote
    manipulation. The safe_call() method is overridable for thread-safety
    in host environments (e.g., Textual's call_from_thread).

    Commands are tuples with a string prefix indicating the namespace:
        source.__call__, source.__keys__, source.__getitem__, source.__setitem__,
        data.__getitem__, data.__setitem__, data.__keys__, data.__delitem__,
        __builders__, __quit__.
    """

    def __init__(self, manager: BuilderManager) -> None:
        self._manager = manager
        self._quit_callback: Callable[[], None] | None = None

    @property
    def manager(self) -> BuilderManager:
        """The wrapped BuilderManager."""
        return self._manager

    def handle_command(self, cmd: tuple[Any, ...]) -> Any:
        """Dispatch a command tuple to the appropriate handler."""
        action = cmd[0]

        if action == "source.__call__":
            builder_name, method_name, args, kwargs = cmd[1], cmd[2], cmd[3], cmd[4]
            return self.safe_call(
                lambda: self._handle_source_call(builder_name, method_name, args, kwargs)
            )

        if action == "source.__keys__":
            return self._handle_source_keys(cmd[1])

        if action == "source.__getitem__":
            return self._handle_source_getitem(cmd[1], cmd[2])

        if action == "source.__setitem__":
            return self.safe_call(
                lambda: self._handle_source_setitem(cmd[1], cmd[2], cmd[3])
            )

        if action == "data.__getitem__":
            return self._handle_data_getitem(cmd[1])

        if action == "data.__setitem__":
            return self.safe_call(
                lambda: self._handle_data_setitem(cmd[1], cmd[2])
            )

        if action == "data.__keys__":
            return self._handle_data_keys()

        if action == "data.__delitem__":
            return self.safe_call(lambda: self._handle_data_delitem(cmd[1]))

        if action == "__builders__":
            return self._handle_builders()

        if action == "__quit__":
            if self._quit_callback is not None:
                self._quit_callback()
            return "quitting"

        raise ValueError(f"Unknown command: {action}")

    def safe_call(self, func: Callable[[], Any]) -> Any:
        """Execute func safely. Override for thread dispatch.

        Default: direct call. Subclasses (e.g., Textual integration)
        override to dispatch to the host event loop thread.
        """
        return func()

    def serve(self, port: int = 0, name: str | None = None) -> LiveServer:
        """Create and start a LiveServer for this session.

        Args:
            port: Port to listen on (0 = auto-select free port).
            name: If given, register this session in the LiveRegistry.

        Returns:
            The started LiveServer instance.
        """
        server = LiveServer(self, port=port)
        server.start()
        if name is not None:
            registry = LiveRegistry()
            registry.register(name, server.port, server.token)
        return server

    def _get_builder_source(self, builder_name: str) -> Any:
        """Get the source Bag for a named builder."""
        builders = self._manager._builders  # type: ignore[attr-defined]
        if builder_name not in builders:
            available = list(builders.keys())
            raise ValueError(
                f"Builder '{builder_name}' not found. Available: {available}"
            )
        return builders[builder_name].source

    def _handle_source_call(
        self, builder_name: str, method_name: str, args: tuple[Any, ...], kwargs: dict[str, Any]
    ) -> None:
        """Call a builder method on the named builder's source.

        Returns None — source mutations produce BagNode objects that
        are not serializable across the wire. The mutation is the effect.
        """
        source = self._get_builder_source(builder_name)
        method = getattr(source, method_name)
        method(*args, **kwargs)

    def _handle_source_keys(self, builder_name: str) -> list[str]:
        """Return keys from the named builder's source."""
        source = self._get_builder_source(builder_name)
        return list(source.keys())

    def _handle_source_getitem(self, builder_name: str, key: str) -> Any:
        """Get item from named builder's source."""
        source = self._get_builder_source(builder_name)
        return source[key]

    def _handle_source_setitem(self, builder_name: str, key: str, value: Any) -> None:
        """Set item on named builder's source."""
        source = self._get_builder_source(builder_name)
        source[key] = value

    def _handle_data_getitem(self, key: str) -> Any:
        """Get value from reactive_store."""
        return self._manager.reactive_store[key]

    def _handle_data_setitem(self, key: str, value: Any) -> None:
        """Set value on reactive_store."""
        self._manager.reactive_store[key] = value

    def _handle_data_keys(self) -> list[str]:
        """List keys in reactive_store."""
        return list(self._manager.reactive_store.keys())

    def _handle_data_delitem(self, key: str) -> None:
        """Delete key from reactive_store."""
        del self._manager.reactive_store[key]

    def _handle_builders(self) -> list[str]:
        """List registered builder names."""
        builders: dict[str, Any] = self._manager._builders  # type: ignore[attr-defined]
        return list(builders.keys())


class LiveServer:
    """TCP socket server for remote control of a LiveSession.

    Runs in a daemon thread. One connection at a time (serialized).
    Authenticates via token (hex string, 16 bytes).
    """

    def __init__(self, session: LiveSession, port: int = 0) -> None:
        self._session = session
        self._requested_port = port
        self._port = port
        self._thread: threading.Thread | None = None
        self._running = False
        self._token = secrets.token_hex(16)
        self._protocol = _FrameProtocol()
        self._server_socket: socket.socket | None = None

    @property
    def token(self) -> str:
        """Authentication token."""
        return self._token

    @property
    def port(self) -> int:
        """Actual listening port (resolved after start if requested 0)."""
        return self._port

    def start(self) -> None:
        """Start the server in a daemon thread."""
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind(("127.0.0.1", self._requested_port))
        srv.listen(5)
        srv.settimeout(1.0)
        self._server_socket = srv
        self._port = srv.getsockname()[1]
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the server and wait for thread to finish."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
        if self._server_socket is not None:
            self._server_socket.close()
            self._server_socket = None

    def _run(self) -> None:
        """Socket accept loop with 1s timeout."""
        assert self._server_socket is not None
        srv = self._server_socket
        while self._running:
            try:
                conn, _ = srv.accept()
            except TimeoutError:
                continue
            except OSError:
                break
            try:
                self._handle_connection(conn)
            finally:
                conn.close()

    def _handle_connection(self, conn: socket.socket) -> None:
        """Handle one connection: receive, auth, dispatch, respond."""
        raw = self._protocol.recv(conn)
        if raw is None:
            return
        try:
            token, cmd = pickle.loads(raw)
        except (pickle.UnpicklingError, ValueError, TypeError):
            response = ("error", "malformed message")
            self._protocol.send(conn, pickle.dumps(response))
            return

        if token != self._token:
            response = ("error", "invalid token")
            self._protocol.send(conn, pickle.dumps(response))
            return

        try:
            result = self._session.handle_command(cmd)
            response = ("ok", result)
        except Exception as exc:
            response = ("error", str(exc))

        self._protocol.send(conn, pickle.dumps(response))
