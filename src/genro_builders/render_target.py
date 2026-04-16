# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""RenderTarget — destination layer for reactive rendering.

A RenderTarget receives rendered output (strings) and writes it
to a destination (file, socket, etc.). Used by the ReactiveManager
to automatically deliver render output when data changes.

Concrete implementations:
    FileRenderTarget — writes to a file path.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


class RenderTarget:
    """Base class for render output destinations.

    Subclass and override ``write()`` to deliver rendered content
    to a specific destination (file, WebSocket, HTTP response, etc.).
    """

    def write(self, content: str) -> Any:
        """Write rendered content to the destination.

        Args:
            content: The rendered output string.
        """
        raise NotImplementedError


class FileRenderTarget(RenderTarget):
    """Write rendered output to a file."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    @property
    def path(self) -> Path:
        """The file path."""
        return self._path

    def write(self, content: str) -> None:
        """Write content to the file (overwrite)."""
        self._path.write_text(content)
