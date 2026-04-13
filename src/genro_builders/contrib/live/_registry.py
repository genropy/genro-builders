# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""File-based registry for live builder sessions.

Stores session info (port, token, pid) as JSON at
``~/.tmp/genro_builders_{uid}/registry.json``.
Uses fcntl file locking for concurrent access and atomic writes
(temp file + rename) for data integrity.
"""
from __future__ import annotations

import fcntl
import json
import os
import socket
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any


class LiveRegistry:
    """File-based session registry with fcntl locking.

    Each entry maps a session name to {port, token, pid}.
    Concurrent reads use shared locks; writes use exclusive locks.
    """

    def __init__(self) -> None:
        self._registry_dir = (
            Path(tempfile.gettempdir()) / f"genro_builders_{os.getuid()}"
        )
        self._registry_file = self._registry_dir / "registry.json"
        self._lock_file = self._registry_dir / ".lock"

    def register(self, name: str, port: int, token: str = "", pid: int | None = None) -> None:
        """Register a live session."""
        if pid is None:
            pid = os.getpid()
        with self._locked(write=True):
            registry = self._load()
            registry[name] = {"port": port, "token": token, "pid": pid}
            self._save(registry)

    def unregister(self, name: str) -> None:
        """Remove a session from the registry."""
        with self._locked(write=True):
            registry = self._load()
            registry.pop(name, None)
            self._save(registry)

    def get_info(self, name: str) -> dict[str, Any] | None:
        """Get full info for a session. Returns None if not found."""
        with self._locked(write=False):
            registry = self._load()
            return registry.get(name)

    def list_all(self) -> dict[str, dict[str, Any]]:
        """List all registered sessions."""
        with self._locked(write=False):
            return self._load()

    def find_free_port(self) -> int:
        """Find an available port on localhost."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(("127.0.0.1", 0))
            port: int = sock.getsockname()[1]
            return port
        finally:
            sock.close()

    def _ensure_dir(self) -> None:
        """Create registry directory with restricted permissions."""
        self._registry_dir.mkdir(mode=0o700, parents=True, exist_ok=True)

    def _load(self) -> dict[str, dict[str, Any]]:
        """Load registry JSON. Must hold lock."""
        if not self._registry_file.exists():
            return {}
        try:
            text = self._registry_file.read_text(encoding="utf-8")
            data = json.loads(text)
        except (json.JSONDecodeError, OSError):
            return {}
        if not isinstance(data, dict):
            return {}
        return data

    def _save(self, registry: dict[str, dict[str, Any]]) -> None:
        """Atomic save: write temp + rename. Must hold lock."""
        self._ensure_dir()
        tmp_path = self._registry_file.with_suffix(".tmp")
        tmp_path.write_text(json.dumps(registry, indent=2), encoding="utf-8")
        tmp_path.chmod(0o600)
        tmp_path.rename(self._registry_file)

    @contextmanager
    def _locked(self, write: bool = False) -> Iterator[None]:
        """Context manager for fcntl-locked registry access."""
        self._ensure_dir()
        lock_op = fcntl.LOCK_EX if write else fcntl.LOCK_SH
        with open(self._lock_file, "a+") as fd:
            try:
                fcntl.flock(fd, lock_op)
                yield
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
