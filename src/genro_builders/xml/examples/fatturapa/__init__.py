# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""FatturaPA example: a dialect generated from an XSD schema (builder + handler preset).

Reference example of the XML transpiler: ``fattura_elettronica.py`` is
generated from ``Schema_VFPA12_V1.2.3.xsd`` and declares
``FatturaElettronicaBuilder`` (grammar) + ``FatturaElettronicaHandler``
(preset). The user subclasses the handler and implements ``main``.
"""

from __future__ import annotations

from .fattura_elettronica import (
    FatturaElettronicaBuilder,
    FatturaElettronicaHandler,
)

__all__ = ["FatturaElettronicaBuilder", "FatturaElettronicaHandler"]
