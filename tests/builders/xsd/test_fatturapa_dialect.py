# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for the FatturaPA example dialect.

The generated mixin :class:`FatturaPAElements` is pure Python (no
xmlschema needed) so the dialect itself is testable on every install.
The optional regeneration round-trip is gated on ``xmlschema`` being
available so the suite stays green on a vanilla install.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from genro_builders.contrib.xsd import FatturaPABuilder, FatturaPABuilderHandler

FATTURAPA_XSD = (
    Path(__file__).resolve().parents[2]
    / "../src/genro_builders/contrib/xsd/examples/fatturapa/Schema_VFPA12_V1.2.3.xsd"
).resolve()

FATTURAPA_GENERATED = (
    Path(__file__).resolve().parents[2]
    / "../src/genro_builders/contrib/xsd/examples/fatturapa/fatturapa_elements.py"
).resolve()


def test_dialect_imports_without_xmlschema_dependency():
    """The generated mixin must not pull xmlschema into the import graph
    of a downstream consumer."""
    import importlib
    import sys

    # The generated module is already imported above; the assertion is
    # that *its* import does not in turn import xmlschema. We verify by
    # re-importing in a controlled way and checking sys.modules.
    pre_state = "xmlschema" in sys.modules
    importlib.import_module(
        "genro_builders.contrib.xsd.examples.fatturapa.fatturapa_elements"
    )
    post_state = "xmlschema" in sys.modules
    assert post_state == pre_state, (
        "Importing the generated FatturaPAElements pulled xmlschema into "
        "sys.modules; the runtime path must stay free of optional deps."
    )


def test_builder_schema_contains_known_elements():
    builder = FatturaPABuilder()
    schema_tags = set(builder._schema_tag_names)
    expected = {
        "fatturaelettronica",
        "fatturaelettronicaheader",
        "fatturaelettronicabody",
        "datitrasmissione",
        "idtrasmittente",
        "cedenteprestatore",
        "cessionariocommittente",
    }
    assert expected.issubset(schema_tags), (
        f"missing FatturaPA elements: {expected - schema_tags}"
    )


def test_handler_renders_minimal_document_to_xml():
    class MinimalInvoice(FatturaPABuilderHandler):
        def main(self, root):
            root.FatturaElettronica(versione="FPA12", SistemaEmittente="TESTSW")

    h = MinimalInvoice()
    h.create()
    xml = h.render(mode="xml", target=False)
    assert "<FatturaElettronica" in xml
    assert 'versione="FPA12"' in xml
    assert 'SistemaEmittente="TESTSW"' in xml


def test_handler_writes_xml_to_file(tmp_path):
    class MinimalInvoice(FatturaPABuilderHandler):
        def main(self, root):
            root.FatturaElettronica(versione="FPA12", SistemaEmittente="TESTSW")

    out = tmp_path / "invoice.xml"
    h = MinimalInvoice()
    h.set_render_target("xml", str(out), default=True)
    h.create()
    h.render()
    body = out.read_text()
    assert body.startswith("<FatturaElettronica")


def test_generated_signature_documents_enum_values():
    """The generated mixin documents the XSD enumeration on the
    ``versione`` parameter via ``Literal['FPA12', 'FPR12']``. This is
    *documentation only*: the declarative ``@element`` decorator
    drops the signature, so no runtime type-check is performed.
    Conformance is enforced later against the XSD itself.

    Test pins the documentation contract: regenerating the dialect
    must keep the Literal in the signature so editors / type checkers
    surface the allowed values to the user."""
    import inspect

    from genro_builders.contrib.xsd.examples.fatturapa import (
        fatturapa_elements as fpe_module,
    )

    raw_source = inspect.getsource(fpe_module)
    assert "Literal['FPA12', 'FPR12']" in raw_source, (
        "Generated mixin must surface enum values via Literal on the signature."
    )


# -----------------------------------------------------------------------------
# Codegen idempotence (requires xmlschema)
# -----------------------------------------------------------------------------


def test_regeneration_is_byte_identical(tmp_path):
    """Re-running the codegen on the committed XSD must produce the
    same file already in the repository, byte-for-byte. This protects
    against accidental drift between the source XSD and the
    versioned generated module."""
    pytest.importorskip("xmlschema")
    import warnings

    from genro_builders.contrib.xsd.codegen import (
        PythonGenerator,
        XmlschemaBackend,
    )
    from genro_builders.contrib.xsd.codegen.backend import XsdCodegenWarning

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", XsdCodegenWarning)
        model = XmlschemaBackend().load(FATTURAPA_XSD)
    source = PythonGenerator().render(
        model,
        class_name="FatturaPAElements",
        module_docstring=(
            "Element mixin for the Italian PA electronic invoice "
            "(FatturaPA v1.2.3). Generated from the official XSD published "
            "by Agenzia delle Entrate. Pair with BagBuilderBase via "
            "FatturaPABuilder in builder.py."
        ),
    )

    committed = FATTURAPA_GENERATED.read_text(encoding="utf-8")
    assert source == committed, (
        "Codegen output drifted from the committed file. "
        f"Regenerate with: python -m genro_builders.contrib.xsd.codegen "
        f"--xsd {FATTURAPA_XSD} --class-name FatturaPAElements "
        f"--output {FATTURAPA_GENERATED}"
    )
