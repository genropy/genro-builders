# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""TargetWrapper — the render destination as an object.

Instead of a raw target (path, writable, callable) the author can
register a wrapper: the render does not know who is behind it, it just
delivers. The wrapper declares what it can consume:

- ``full(document)`` — the result of a total render. Every wrapper
  supports it.
- ``partial(patches)`` — a batch of per-node patches, delivered by the
  ``live()`` flush when ``accepts_partial`` is True. Patch ids are
  ``target_id`` serials — the same string the reactive render emits as
  the DOM id under ``include_datapath``. The ops: ``replace`` carries
  the re-rendered node (outer fragment, attributes included);
  ``insert`` the new child only (``{"id": container, "before":
  sibling id | None, "html"}``); ``remove`` just the id. The
  vocabulary is open: finer ops (``set_attrs``, ``set_text``) ride
  the same envelope when the per-attribute granularity lands.

``render_opts`` are the walk options every delivery render uses — the
destination dictates the form (a patch consumer needs the DOM ids, so
``{"include_datapath": True}``).

A raw target keeps working everywhere a wrapper does: the renderer's
``finalize`` consumes both. The wrapper exists so that "total vs
partial" is a property of the destination, not an if in the renderer:
a file is total by nature; a partial-aware consumer applies patches;
a probe collects them in tests.
"""
from __future__ import annotations

from typing import Any, ClassVar


class TargetWrapper:
    """Base wrapper: declares the delivery contract of a destination."""

    #: True when the destination can consume per-node patches; the
    #: live() flush consults it and falls back to a full render when
    #: False.
    accepts_partial: bool = False

    #: Walk options for every render delivered to this destination.
    render_opts: ClassVar[dict[str, Any]] = {}

    def full(self, document: Any) -> None:
        """Consume the result of a total render."""
        raise NotImplementedError(
            f"{type(self).__name__} does not implement full()",
        )

    def partial(self, patches: list[dict[str, Any]]) -> None:
        """Consume a batch of per-node patches (one live section)."""
        raise NotImplementedError(
            f"{type(self).__name__} declares accepts_partial but does "
            "not implement partial()",
        )
