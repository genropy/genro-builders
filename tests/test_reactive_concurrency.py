# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Concurrency bench for the reactive model (Application skeleton).

Two tests, two distinct purposes:

1. ``test_concurrent_mutations_keep_area_consistent`` — exercises the
   MODEL: several named threads mutate ``base``/``altezza`` through the
   app's session, the reactive formula recomputes ``area``, and at rest the
   invariant ``area == base*altezza/2`` holds. This proves the app /
   session / proxy / reactive-formula stack works under threads (no
   deadlock, no crash, no incoherent state). It does NOT prove the lock is
   needed — single ``set_item`` writes are covered by the GIL anyway.

2. ``test_session_serializes_read_modify_write`` — the actual LOCK guard.
   A read-modify-write of a counter, with a sleep between read and write,
   is atomic ONLY because the session holds the per-handler lock for the
   whole block. Without the lock another thread slips in during the sleep
   (the GIL yields there), increments are lost, and the final count drops
   below ``N*iter``. If a refactor ever removes the lock from ``live()``,
   this test fails. With the lock the final count is exact.

Determinism: seeded ``random.Random`` per worker, fixed iteration counts;
finite and reproducible. Sleeps stagger the threads to force contention.
"""

from __future__ import annotations

import random
import threading
import time

from tests.reactive_app import MiniApp

# --- test 1: the model under concurrency -----------------------------------

# (name, target data path, seed, per-iteration sleep seconds)
_WORKERS = [
    ("base-fast", "tri.base", 1, 0.003),
    ("base-slow", "tri.base", 2, 0.012),
    ("altezza-mid", "tri.altezza", 3, 0.005),
    ("altezza-fast", "tri.altezza", 4, 0.004),
]
_ITERATIONS = 40


def _run_worker(app: MiniApp, path: str, seed: int, pause: float) -> None:
    rng = random.Random(seed)
    for _ in range(_ITERATIONS):
        value = rng.randint(1, 20)
        with app.session() as proxy:
            proxy.data.set_item(path, value)
        time.sleep(pause)  # outside the session: pacing, no mutation


def test_concurrent_mutations_keep_area_consistent():
    """Many threads mutate base/altezza; the reactive area stays consistent
    at rest. Proves the app/session/proxy/formula model holds under threads."""
    app = MiniApp()

    threads = [
        threading.Thread(
            target=_run_worker, args=(app, path, seed, pause), name=name,
        )
        for name, path, seed, pause in _WORKERS
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Quiescent state: re-read and check the invariant for any interleaving.
    base = app.handler.data.get_item("tri.base")
    altezza = app.handler.data.get_item("tri.altezza")
    area = app.handler.data.get_item("tri.area")
    assert area == base * altezza / 2


# --- test 2: the lock guard (read-modify-write atomicity) ------------------

_RMW_THREADS = 4
_RMW_ITER = 10
_RMW_SLEEP = 0.002  # widens the read->write window so a missing lock loses writes


def _increment_worker(app: MiniApp) -> None:
    for _ in range(_RMW_ITER):
        with app.session() as proxy:
            current = proxy.data.get_item("counter")
            time.sleep(_RMW_SLEEP)  # inside the session: protected by the lock
            proxy.data.set_item("counter", current + 1)


def test_session_serializes_read_modify_write():
    """A read-modify-write inside the session is atomic because the lock is
    held for the whole block. Lose the lock and the increments race away."""
    app = MiniApp()
    app.handler.data.set_item("counter", 0)

    threads = [
        threading.Thread(target=_increment_worker, args=(app,), name=f"inc-{i}")
        for i in range(_RMW_THREADS)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert app.handler.data.get_item("counter") == _RMW_THREADS * _RMW_ITER
