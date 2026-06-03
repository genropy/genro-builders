# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""XSD contrib — base classes + codegen pipeline + example dialect.

XSD-born dialects are real builders whose grammar is a schema's element
vocabulary and whose on-the-wire format is XML. Two light base classes
anchor them: :class:`XsdBuilderBase` (grammar, ``xml`` default mode) and
:class:`XsdHandler` (engine preset). The XML render itself is the core's
real ``XmlRenderer`` — pointers resolved, framework markers filtered.

The **codegen** pipeline (see ``codegen/``) turns an XSD file into a Python
module declaring a ``<Dialect>Builder(XsdBuilderBase)`` +
``<Dialect>Handler(XsdHandler)`` pair, shipped as committed source. The
generated module has **no** runtime dependency on ``xmlschema``; only the
codegen needs the ``[xsd]`` optional extra. The codegen produces a
*starting base*: constraints the grammar cannot yet express (e.g.
``totalDigits``) and XSD patterns Python's ``re`` cannot compile (Unicode
block properties) are surfaced as ``# NOTE:`` comments for hand-refinement,
not silently dropped nor emitted as broken code.

The bundled :class:`FatturaElettronicaHandler` is the reference example:
a generated dialect for the Italian PA electronic invoice
(``Schema_VFPA12_V1.2.3.xsd``).

Example::

    from genro_builders.contrib.xsd import FatturaElettronicaHandler

    class MyInvoice(FatturaElettronicaHandler):
        def main(self, root):
            root.FatturaElettronica(versione="FPA12", SistemaEmittente="MYSYS")

    invoice = MyInvoice()
    invoice.create()
    print(invoice.render(mode="xml", target=False))
"""

from __future__ import annotations

# Only the base classes live at the package root. The example dialect
# (``FatturaElettronicaHandler``) is imported from its own module —
# ``contrib.xsd.examples.fatturapa`` — not re-exported here: a generated
# dialect imports the bases from ``.xsd_builder`` and re-exporting the
# example would create an import cycle (package → example → bases → package).
from .xsd_builder import XsdBuilderBase, XsdHandler

__all__ = [
    "XsdBuilderBase",
    "XsdHandler",
]
