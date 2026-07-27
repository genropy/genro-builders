# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""FatturaPA example: a dialect generated from an XSD schema.

Reference example of the XML transpiler: ``fattura_elettronica.py`` is
generated from ``Schema_VFPA12_V1.2.3.xsd`` and declares
``FatturaElettronicaBuilder`` (grammar). The user subclasses it,
implements ``main``, and creates and renders the subclass.
"""

from __future__ import annotations

from .fattura_elettronica import FatturaElettronicaBuilder

__all__ = ["FatturaElettronicaBuilder"]
