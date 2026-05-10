# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Build pipeline. To be reimplemented per 2026-05-03/04 decisions.

The build phase materializes the source Bag (the user's recipe, with
``@component`` nodes left opaque) into the built Bag (components
expanded, pointers resolved). In the new architecture the pipeline is
driven by the BuilderHandler and lives on the concrete builder
(decision 5: ``builder.build(source, built)``).

This module is a placeholder during the restart: it keeps the file in
the package layout while the build algorithm is rewritten in the
contrib builders. ``_BuildMixin`` is still inherited by
``BagBuilderBase`` so the MRO remains stable; its methods are no-ops.
"""

from __future__ import annotations


class _BuildMixin:
    """Build pipeline. Reimplemented per 2026-05-03/04 decisions."""

    def build(self) -> None:
        """Materialize source into built. Reimplemented in fase 2."""

    def new_built(self):
        """Return a fresh built bag. Reimplemented in fase 2."""
