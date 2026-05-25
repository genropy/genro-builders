# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""XSD contrib — codegen pipeline + generated example dialects.

The XSD support in ``genro-builders`` is a **codegen** pipeline, not
a runtime XSD interpreter. Given an XSD file you generate a static
Python builder mixin (see ``codegen/``), pair it with
:class:`~genro_builders.builder.BagBuilderBase` in a concrete builder
class, and ship the result as committed source. Generated dialects
have **no** runtime dependency on ``xmlschema``; only the codegen
itself needs the ``[xsd]`` optional extra.

The bundled :class:`FatturaPABuilderHandler` is the reference example:
a fully generated dialect for the Italian PA electronic invoice
(``Schema_VFPA12_V1.2.3.xsd``).

Example::

    from genro_builders.contrib.xsd import FatturaPABuilderHandler

    class MyInvoice(FatturaPABuilderHandler):
        def main(self, root):
            root.FatturaElettronica(versione="FPA12", SistemaEmittente="MYSYS")

    invoice = MyInvoice()
    invoice.create()
    print(invoice.render(mode="xml", target=False))
"""

from __future__ import annotations

from .examples.fatturapa import FatturaPABuilder, FatturaPABuilderHandler

__all__ = ["FatturaPABuilder", "FatturaPABuilderHandler"]
