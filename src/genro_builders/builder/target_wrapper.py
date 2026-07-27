# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""TargetWrapper — the render destination as an object.

Instead of a raw target (path, writable, callable) the author can
register a wrapper: the render does not know who is behind it, it just
delivers. The wrapper declares two things:

- ``full(document)`` — how to consume the result of a render.
- ``render_opts`` — the walk options every delivery to this destination
  uses, because the destination dictates the form of the document (a
  consumer that needs the DOM ids asks for
  ``{"include_datapath": True}``).

The renderer's ``finalize`` consumes both a raw target and a wrapper.
The wrapper exists so that "how this destination wants the document" is
a property of the destination, not an if in the renderer.

There is no concrete subclass in the package: the base class is the
extension point a host application implements.
"""
from __future__ import annotations

from typing import Any, ClassVar


class TargetWrapper:
    """Base wrapper: declares the delivery contract of a destination."""

    #: Walk options for every render delivered to this destination.
    render_opts: ClassVar[dict[str, Any]] = {}

    def full(self, document: Any) -> None:
        """Consume the result of a render."""
        raise NotImplementedError(
            f"{type(self).__name__} does not implement full()",
        )
