# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""ReactiveManager tests (Tranche B, Fase 4).

Covers the per-builder subscribe model: each registered builder's
``local_store`` Bag is subscribed independently. Changes flow through
``_on_store_changed`` → ``_flush`` → ``on_data_changed(impacted)``.

Sync-flush tests cover the no-event-loop path (immediate flush).
The multi-store coalescing test runs under ``asyncio.run`` to exercise
the ``call_soon`` path.
"""

from __future__ import annotations

import asyncio
from typing import Any

from genro_builders import ReactiveManager
from genro_builders.dependency_graph import DepEdge
from tests.helpers import TestBuilder as _Builder


class _RecordingApp(ReactiveManager):
    """A ReactiveManager that records every ``on_data_changed`` call."""

    def __init__(self) -> None:
        self.dispatches: list[dict[str, str]] = []
        super().__init__()

    def on_init(self) -> None:
        self.register_builder("page", _Builder)
        self.register_builder("sidebar", _Builder)

    def on_data_changed(self, impacted: dict[str, str]) -> None:
        self.dispatches.append(dict(impacted))


def _add_render_edge(app: _RecordingApp, source_path: str, builder: str) -> None:
    """Helper: install a render edge so a path change impacts a builder."""
    app.dep_graph.add(DepEdge(
        source_path=source_path,
        target=f"{builder}.x",
        dep_type="render",
        builder_name=builder,
    ))


class TestSubscribeAttachesToEachStore:
    """``subscribe()`` attaches to every registered builder's local_store."""

    def test_subscribe_attaches_to_each_local_store(self) -> None:
        app = _RecordingApp()
        app.subscribe()

        sub_id = app._SUBSCRIBER_ID
        for name in ("page", "sidebar"):
            store = app.resolve_volume(name)
            assert sub_id in store._ins_subscribers
            assert sub_id in store._upd_subscribers
            assert sub_id in store._del_subscribers

    def test_subscribe_is_idempotent(self) -> None:
        app = _RecordingApp()
        _add_render_edge(app, "title", "page")
        app.subscribe()
        app.subscribe()

        # Calling subscribe twice must not double-register.
        app.resolve_volume("page").set_item("title", "x")
        # Exactly one dispatch — not two from a duplicated subscriber.
        assert len(app.dispatches) == 1


class TestUnsubscribeDetachesAllStores:
    """``unsubscribe()`` removes the subscriber from every store."""

    def test_unsubscribe_detaches_all_stores(self) -> None:
        app = _RecordingApp()
        app.subscribe()
        app.unsubscribe()

        sub_id = app._SUBSCRIBER_ID
        for name in ("page", "sidebar"):
            store = app.resolve_volume(name)
            assert sub_id not in store._ins_subscribers
            assert sub_id not in store._upd_subscribers
            assert sub_id not in store._del_subscribers

    def test_unsubscribe_clears_pending_changes(self) -> None:
        app = _RecordingApp()
        app.subscribe()
        app._pending_changes.append("phantom")
        app.unsubscribe()

        assert app._pending_changes == []
        assert app._flush_scheduled is False


class TestSyncDispatch:
    """In sync context (no event loop), ``_flush`` runs immediately."""

    def test_change_in_one_store_dispatches(self) -> None:
        app = _RecordingApp()
        _add_render_edge(app, "title", "page")
        app.subscribe()

        app.resolve_volume("page").set_item("title", "hello")

        assert app.dispatches == [{"page": "render"}]

    def test_change_in_unrelated_store_does_not_dispatch(self) -> None:
        app = _RecordingApp()
        _add_render_edge(app, "title", "page")
        app.subscribe()

        # No edge registered for sidebar paths.
        app.resolve_volume("sidebar").set_item("foo", "bar")

        assert app.dispatches == []

    def test_dispatching_flag_blocks_reentrancy(self) -> None:
        """While ``on_data_changed`` runs, further store mutations are
        not re-collected — the ``_dispatching`` guard prevents the
        callback from re-entering the queue.
        """
        recorded: list[Any] = []

        class App(_RecordingApp):
            def on_data_changed(self, impacted: dict[str, str]) -> None:
                recorded.append(dict(impacted))
                # Mutating a store from inside the callback must not loop.
                self.resolve_volume("page").set_item("title", "again")

        app = App()
        _add_render_edge(app, "title", "page")
        app.subscribe()

        app.resolve_volume("page").set_item("title", "first")

        # Exactly one dispatch — the inner mutation is suppressed by the
        # _dispatching guard.
        assert len(recorded) == 1


class TestAsyncCoalescing:
    """Under an event loop, multiple changes in the same tick coalesce
    into a single ``on_data_changed`` call.
    """

    def test_two_stores_same_tick_one_dispatch(self) -> None:
        async def scenario() -> _RecordingApp:
            app = _RecordingApp()
            _add_render_edge(app, "title", "page")
            _add_render_edge(app, "color", "sidebar")
            app.subscribe()

            # Both mutations happen synchronously inside the same tick.
            app.resolve_volume("page").set_item("title", "T")
            app.resolve_volume("sidebar").set_item("color", "red")

            # Yield to the event loop so the scheduled call_soon fires.
            await asyncio.sleep(0)
            return app

        app = asyncio.run(scenario())

        assert len(app.dispatches) == 1
        assert app.dispatches[0] == {"page": "render", "sidebar": "render"}

    def test_changes_in_different_ticks_dispatch_separately(self) -> None:
        async def scenario() -> _RecordingApp:
            app = _RecordingApp()
            _add_render_edge(app, "title", "page")
            app.subscribe()

            app.resolve_volume("page").set_item("title", "T1")
            await asyncio.sleep(0)

            app.resolve_volume("page").set_item("title", "T2")
            await asyncio.sleep(0)
            return app

        app = asyncio.run(scenario())

        assert len(app.dispatches) == 2
        assert app.dispatches[0] == {"page": "render"}
        assert app.dispatches[1] == {"page": "render"}
