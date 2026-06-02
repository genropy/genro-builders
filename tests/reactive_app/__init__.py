# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Skeleton of the Application model — a concurrency test bench.

Three collaborating classes exercise the reactive model end to end:

- :class:`MiniApp` — the Application: the layer between the outside world
  and the handler. It owns the handler (dual relationship: it passes itself
  in) and hands out a restricted *proxy* through a context-managed session,
  never the bare handler.
- :class:`TrianglePage` — an ``HtmlBuilderHandler`` whose data-formula
  computes the area of a triangle from ``base`` and ``altezza``.
- :class:`DataLogic` — the named ``@staticmethod`` functions the formulas
  resolve through ``data_logic``.

The bench (``tests/test_reactive_concurrency.py``) spawns several named
threads that mutate ``base``/``altezza`` at different cadences through the
app's session; the per-handler lock serializes them. The assertion is a
quiescent-state invariant (``area == base*altezza/2``), independent of the
interleaving.
"""

from .app import MiniApp
from .logic import DataLogic
from .page import TrianglePage

__all__ = ["DataLogic", "MiniApp", "TrianglePage"]
