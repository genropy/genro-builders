# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""DataLogic — named functions resolved by the data-elements.

A data-element ``func`` is a ``@staticmethod`` resolved by NAME over the
handler's ``data_logic`` sources. The page wires this class in via
``_build_data_logic`` so ``dataFormula(..., "calc_area", ...)`` finds it.
"""

from __future__ import annotations


class DataLogic:
    """Computation functions for the triangle page."""

    @staticmethod
    def calc_area(base: float, altezza: float) -> float:
        """Triangle area from base and height."""
        return base * altezza / 2
