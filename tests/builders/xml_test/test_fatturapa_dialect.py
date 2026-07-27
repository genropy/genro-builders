# Copyright 2025 Softwell S.r.l. - SPDX-License-Identifier: Apache-2.0
"""Tests for the FatturaPA example dialect.

The generated dialect (``FatturaElettronicaBuilder`` + ``...Handler``) is
pure Python (no xmlschema needed), so it is testable on every install.
The optional regeneration round-trip is gated on ``xmlschema`` being
available so the suite stays green on a vanilla install.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from genro_builders.builder import BuilderHandler
from genro_builders.xml.examples.fatturapa import FatturaElettronicaBuilder

_FATTURAPA_DIR = (
    Path(__file__).resolve().parents[2]
    / "../src/genro_builders/xml/examples/fatturapa"
).resolve()
FATTURAPA_XSD = _FATTURAPA_DIR / "Schema_VFPA12_V1.2.3.xsd"
FATTURAPA_GENERATED = _FATTURAPA_DIR / "fattura_elettronica.py"

_MODULE_DOCSTRING = (
    "FatturaPA v1.2.3 dialect (Italian PA electronic invoice). Generated "
    "from the official Schema_VFPA12_V1.2.3.xsd published by Agenzia delle "
    "Entrate. Some XSD patterns use Unicode block properties that Python re "
    "cannot compile; those validators are commented out for hand-refinement."
)


def test_dialect_imports_without_xmlschema_dependency():
    """The generated module must not pull xmlschema into the import graph
    of a downstream consumer."""
    import importlib
    import sys

    pre_state = "xmlschema" in sys.modules
    importlib.import_module(
        "genro_builders.xml.examples.fatturapa.fattura_elettronica"
    )
    post_state = "xmlschema" in sys.modules
    assert post_state == pre_state, (
        "Importing the generated dialect pulled xmlschema into sys.modules; "
        "the runtime path must stay free of optional deps."
    )


def test_builder_schema_contains_known_elements():
    builder = FatturaElettronicaBuilder()
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
    """A minimal invoice renders to XML. The ``\\p{...}`` patterns are no
    longer emitted as broken validators (issue #30): the codegen comments
    them out, so construction succeeds."""

    class MinimalInvoice(FatturaElettronicaBuilder):
        def main(self, root):
            root.FatturaElettronica(versione="FPA12", SistemaEmittente="TESTSW")

    page = MinimalInvoice()
    BuilderHandler().add_builder(page)
    # attribute-serialization test on a deliberately partial document
    xml = page.render(mode="xml", target=False)
    assert "<FatturaElettronica" in xml
    assert 'versione="FPA12"' in xml
    assert 'SistemaEmittente="TESTSW"' in xml


def test_handler_writes_xml_to_file(tmp_path):
    class MinimalInvoice(FatturaElettronicaBuilder):
        def main(self, root):
            root.FatturaElettronica(versione="FPA12", SistemaEmittente="TESTSW")

    out = tmp_path / "invoice.xml"
    page = MinimalInvoice()
    page.set_render_target(str(out), "xml")
    BuilderHandler().add_builder(page)
    page.render()   # deliberately partial document
    body = out.read_text()
    assert body.startswith("<FatturaElettronica")


def test_incompatible_pattern_is_commented_not_emitted():
    """Issue #30: XSD Unicode-block patterns (``\\p{IsBasicLatin}``) cannot
    compile under Python ``re``. The codegen must NOT emit them as active
    ``Regex(...)`` validators (which would raise at construction); they are
    surfaced as ``# NOTE:`` comments for hand-refinement instead."""
    source = FATTURAPA_GENERATED.read_text(encoding="utf-8")
    # No active validator carries an unsupported \p{...} property.
    for line in source.splitlines():
        if line.lstrip().startswith("#"):
            continue
        assert "\\p{" not in line, (
            f"active line still carries an unsupported \\p{{...}} pattern: {line}"
        )
    # The dropped patterns are documented as refinement notes.
    assert "not Python-re-compatible" in source


def test_generated_signature_documents_enum_values():
    """The generated grammar documents the XSD enumeration on the
    ``versione`` parameter via ``Literal['FPA12', 'FPR12']`` (documentation
    only: the declarative ``@element`` drops the signature at runtime)."""
    import inspect

    from genro_builders.xml.examples.fatturapa import (
        fattura_elettronica as fe_module,
    )

    raw_source = inspect.getsource(fe_module)
    assert "Literal['FPA12', 'FPR12']" in raw_source, (
        "Generated dialect must surface enum values via Literal on the signature."
    )


# -----------------------------------------------------------------------------
# Codegen idempotence (requires xmlschema)
# -----------------------------------------------------------------------------


def test_regeneration_is_byte_identical():
    """Re-running the codegen on the committed XSD must produce the
    file already in the repository, byte-for-byte — guarding against
    drift between the source XSD and the versioned generated module."""
    pytest.importorskip("xmlschema")
    import warnings

    from genro_builders.xml.transpiler import (
        PythonGenerator,
        XmlschemaBackend,
    )
    from genro_builders.xml.transpiler.backend import XsdCodegenWarning

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", XsdCodegenWarning)
        model = XmlschemaBackend().load(FATTURAPA_XSD)
    source = PythonGenerator().render(
        model,
        dialect_name="FatturaElettronica",
        module_docstring=_MODULE_DOCSTRING,
    )

    committed = FATTURAPA_GENERATED.read_text(encoding="utf-8")
    assert source == committed, (
        "Codegen output drifted from the committed file. Regenerate with: "
        f"python -m genro_builders.xml.transpiler --xsd {FATTURAPA_XSD} "
        f"--dialect-name FatturaElettronica --output {FATTURAPA_GENERATED}"
    )


def test_validate_source_reports_an_incomplete_invoice():
    """The XSD minimums become real guarantees — when the author asks.

    Rendering does not validate: a partial document renders. The check is
    a step of its own, called on the source.
    """

    class MinimalInvoice(FatturaElettronicaBuilder):
        def main(self, root):
            root.FatturaElettronica(versione="FPA12")

    page = MinimalInvoice()
    BuilderHandler().add_builder(page)
    problems = page.validate_source()
    missing = [tag for _path, tags in problems for tag in tags]
    assert "FatturaElettronicaHeader" in missing
    # the same document renders without a sound
    assert "<FatturaElettronica" in page.render(mode="xml", target=False)
