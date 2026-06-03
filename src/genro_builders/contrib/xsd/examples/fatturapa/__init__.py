# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""FatturaPA example: a generated XSD dialect (builder + handler preset).

Reference example of the codegen pipeline: ``fattura_elettronica.py`` is
generated from ``Schema_VFPA12_V1.2.3.xsd`` and declares
``FatturaElettronicaBuilder`` (grammar) + ``FatturaElettronicaHandler``
(preset). The user subclasses the handler and implements ``main``.
"""

from __future__ import annotations

from genro_builders.contrib.xsd.examples.fatturapa.fattura_elettronica import (
    FatturaElettronicaBuilder,
    FatturaElettronicaHandler,
)

__all__ = ["FatturaElettronicaBuilder", "FatturaElettronicaHandler"]
