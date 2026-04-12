# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""ReactiveManager — async-capable manager with reactive bindings.

Extends BuilderManager with ``subscribe()`` to activate reactive bindings
(formula re-execution, _delay debounce, _interval timers) on all builders.

Reactivity requires an event loop — use ReactiveManager when the host
environment provides one (Textual, ASGI, Jupyter, asyncio.run).
For one-shot sync pipelines (reports, exports), use BuilderManager.

Lifecycle:
    1. ``__init__``: create builders via ``set_builder()``.
    2. ``setup()``: populate data and source (inherited from BuilderManager).
    3. ``build()``: materialize all builders (inherited from BuilderManager).
    4. ``subscribe()``: activate reactive bindings on all builders.

Single-call shortcut::

    manager.run(subscribe=True)

Example::

    >>> class LiveDashboard(ReactiveManager):
    ...     def __init__(self):
    ...         self.page = self.set_builder('page', HtmlBuilder)
    ...         self.run(subscribe=True)
    ...
    ...     def store(self, data):
    ...         data['count'] = 0
    ...
    ...     def main(self, source):
    ...         source.div(value='^count')
    ...
    >>> dash = LiveDashboard()
    >>> dash.reactive_store['count'] = 42  # triggers re-render
"""
from __future__ import annotations

import inspect
from typing import Any

from genro_toolbox import smartawait

from genro_builders.manager import BuilderManager


class ReactiveManager(BuilderManager):
    """BuilderManager with reactive bindings support.

    Adds ``subscribe()`` to activate reactive data binding on all
    registered builders. Use this when your host environment provides
    an event loop (Textual, ASGI, Jupyter, asyncio.run).

    For one-shot sync pipelines, use BuilderManager directly.
    """

    def subscribe(self) -> None:
        """Activate reactive bindings on all builders.

        Enables formula re-execution on data changes, ``_delay``
        debounce, ``_interval`` periodic execution, and
        ``suspend_output`` / ``resume_output`` for batched rendering.
        """
        for builder in self._builders.values():
            builder.subscribe()

    def run(self, *, subscribe: bool = False) -> Any:
        """Setup, build, and optionally subscribe -- single-call lifecycle.

        Returns None when all builders are synchronous, or a coroutine
        when any builder's build() returns an awaitable.
        In async case, caller must: ``await smartawait(manager.run())``.

        Args:
            subscribe: If True, also activate reactive bindings after build.
        """
        self.setup()
        build_result = self.build()

        if inspect.isawaitable(build_result):
            async def cont():
                await smartawait(build_result)
                if subscribe:
                    self.subscribe()

            return cont()

        if subscribe:
            self.subscribe()
        return None
