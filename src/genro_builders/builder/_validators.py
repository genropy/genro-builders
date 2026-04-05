# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Validator classes for use with ``Annotated`` type hints.

Provides ``Regex`` (pattern constraint for strings) and ``Range``
(min/max constraint for numbers) as frozen dataclasses that can be
attached to element parameters via ``Annotated[T, validator]``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class Regex:
    """Regex pattern constraint for string validation."""

    pattern: str
    flags: int = 0

    def __call__(self, value: Any) -> None:
        if not isinstance(value, str):
            raise TypeError("Regex validator requires a str")
        if re.fullmatch(self.pattern, value, self.flags) is None:
            raise ValueError(f"must match pattern '{self.pattern}'")


@dataclass(frozen=True)
class Range:
    """Range constraint for numeric validation (Pydantic-style: ge, le, gt, lt)."""

    ge: float | None = None
    le: float | None = None
    gt: float | None = None
    lt: float | None = None

    def __call__(self, value: Any) -> None:
        if not isinstance(value, (int, float, Decimal)):
            raise TypeError("Range validator requires int, float or Decimal")
        if self.ge is not None and value < self.ge:
            raise ValueError(f"must be >= {self.ge}")
        if self.le is not None and value > self.le:
            raise ValueError(f"must be <= {self.le}")
        if self.gt is not None and value <= self.gt:
            raise ValueError(f"must be > {self.gt}")
        if self.lt is not None and value >= self.lt:
            raise ValueError(f"must be < {self.lt}")
