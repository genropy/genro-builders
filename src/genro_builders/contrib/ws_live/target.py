# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""WsTargetWrapper — the connection-side render destination.

The page registers this wrapper as its render target: the full render
(activate) lands in ``last_full`` — the HTML the ``main`` WSX call
returns to the client — and every live() flush appends its patch batch,
drained by the ``mutate`` response with :meth:`take`. Delivery over the
response is step one; pushing the batches over the websocket from any
live section (server-initiated reactivity) is the planned refinement —
the wrapper is already the single seam where that lands.
"""
from __future__ import annotations

from typing import Any, ClassVar

from genro_builders.builder import TargetWrapper


class WsTargetWrapper(TargetWrapper):
    """Buffers full documents and patch batches for the WSX cycle."""

    accepts_partial = True
    render_opts: ClassVar[dict[str, Any]] = {"include_datapath": True}

    def __init__(self) -> None:
        self.last_full: str | None = None
        self._patches: list[dict[str, Any]] = []

    def full(self, document: Any) -> None:
        self.last_full = document

    def partial(self, patches: list[dict[str, Any]]) -> None:
        self._patches.extend(patches)

    def take(self) -> list[dict[str, Any]]:
        """Drain and return the buffered patches."""
        out, self._patches = self._patches, []
        return out
