# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""FatturaPA example: generated dialect + concrete builder + handler preset."""

from __future__ import annotations

from genro_builders.contrib.xsd.examples.fatturapa.builder import (
    FatturaPABuilder,
    FatturaPABuilderHandler,
)
from genro_builders.contrib.xsd.examples.fatturapa.fatturapa_elements import (
    FatturaPAElements,
)

__all__ = ["FatturaPABuilder", "FatturaPABuilderHandler", "FatturaPAElements"]
