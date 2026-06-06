# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""MiniApp — the minimal Application and its handler proxy.

The Application is the layer between the outside world and the handler.
It owns the handler (dual relationship: it creates it passing itself in)
and never exposes it bare. Callers reach the handler only through
:meth:`session`, a context manager that holds the per-handler lock for the
duration of the block and yields a :class:`_HandlerProxy` — a restricted
view, not the handler itself.

The proxy filters access via ``__getattr__`` with a whitelist + blacklist +
a policy for the grey zone (names in neither list). In this skeleton the
grey-zone policy is permissive and *logs* each access, so the real boundary
can be discovered from use, then tightened. What the proxy ultimately
exposes (raw ``source``/``data`` bags vs curated actions) is still open.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from .page import TrianglePage

# Always allowed through the proxy (the data the caller mutates).
_WHITELIST: frozenset[str] = frozenset({"source", "data"})
# Never allowed: lifecycle / wiring the caller must not touch mid-session.
_BLACKLIST: frozenset[str] = frozenset({"create", "live", "application"})


class _HandlerProxy:
    """Restricted view over a handler, yielded inside a session.

    Forwards attribute access to the wrapped handler, gated by the
    whitelist/blacklist. Names in neither list fall in the grey zone:
    permitted for now, but recorded in :attr:`grey_accesses` so the real
    boundary can be discovered and then tightened.
    """

    def __init__(self, handler: TrianglePage) -> None:
        # Own attributes are set via __dict__ to avoid the __getattr__ loop;
        # __getattr__ only fires for names NOT found on the instance.
        self.__dict__["_handler"] = handler
        self.__dict__["grey_accesses"] = []

    def __getattr__(self, name: str) -> Any:
        if name in _BLACKLIST:
            raise AttributeError(
                f"{name!r} is not accessible through the handler proxy",
            )
        if name not in _WHITELIST:
            # Grey zone: permitted in this skeleton, but recorded.
            self.__dict__["grey_accesses"].append(name)
        return getattr(self.__dict__["_handler"], name)


class MiniApp:
    """Minimal Application owning one reactive handler."""

    def __init__(self) -> None:
        # Dual relationship: create the handler passing self in, so the
        # handler knows its application (and is therefore reactive).
        self.handler = TrianglePage(application=self)
        self.handler.create()
        # First render finishes startup: it populates the pointer_map (read
        # time) and enables live(). Until a page has rendered it is not reactive.
        self.handler.render(target=False)

    def set_render_target(self, mode: str, target: Any, default: bool = False) -> None:
        """Register a render target on the owned handler."""
        self.handler.set_render_target(mode, target, default=default)

    def render(self, **opts: Any) -> Any:
        """Render the owned handler (read-only, no session needed)."""
        return self.handler.render(**opts)

    @contextmanager
    def session(self) -> Iterator[_HandlerProxy]:
        """Acquire the handler for a mutation block, yielding a proxy.

        The whole handler is held for the duration via ``live()`` (per-handler
        RLock): concurrent callers are serialized, one session at a time. The
        yielded proxy is the only handle to mutate from — the bare handler is
        never exposed.
        """
        with self.handler.live():
            yield _HandlerProxy(self.handler)
