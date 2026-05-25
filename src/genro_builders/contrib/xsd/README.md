# XSD support

The XSD contribution is a **codegen** pipeline: given an XSD schema,
it generates a static Python builder mixin that you commit to your
repository and import without runtime dependencies on the parser.

## Install

```bash
pip install genro-builders            # use generated dialects
pip install 'genro-builders[xsd]'     # also enable the codegen tool
```

The `[xsd]` extra installs `xmlschema` and is required **only** to
run the codegen. Importing or using a dialect already generated and
committed (such as the bundled FatturaPA example) does not need the
extra.

## Quick start — bundled FatturaPA example

```python
from genro_builders.contrib.xsd import FatturaPABuilderHandler


class MyInvoice(FatturaPABuilderHandler):
    def main(self, root):
        root.FatturaElettronica(versione="FPA12", SistemaEmittente="MYSYS")


invoice = MyInvoice()
invoice.create()
print(invoice.render(mode="xml", target=False))
```

## Generating a new dialect

```bash
python -m genro_builders.contrib.xsd.codegen \
    --xsd path/to/schema.xsd \
    --class-name MySchemaElements \
    --output path/to/my_schema_elements.py
```

The resulting module is a mixin class (`MySchemaElements`) with one
`@element` per XSD element. Pair it with `BagBuilderBase` in a
concrete builder:

```python
from genro_builders.builder import BagBuilderBase
from genro_builders.builder_handler import BuilderHandler
from .my_schema_elements import MySchemaElements


class MyBuilder(BagBuilderBase, MySchemaElements):
    _default_render_mode = "xml"


class MyBuilderHandler(BuilderHandler):
    builder_class = MyBuilder
```

See `examples/fatturapa/builder.py` for the reference layout.

## What is and isn't generated

The codegen reads every XSD construct exposed by `xmlschema` and
records them in an intermediate model. It emits as builder grammar:

- one `@element` per element (global + locally declared in complex
  types);
- `sub_tags='a[1],b[0:],c[1:5]'` with explicit cardinalities;
- attributes as call-args with `Literal[...]` for enumerations and
  `Annotated[..., Regex(...)]` / `Annotated[..., Range(...)]` for
  pattern / minInclusive / maxInclusive facets.

The codegen records but does **not** emit (current grammar limits):

- `xs:include` / `xs:import` of additional namespaces (a warning
  surfaces when the source XSD declares them);
- `substitutionGroup`, `xsi:type` discriminators, `xs:any`;
- `minLength` / `maxLength` / `totalDigits` / `fractionDigits` — they
  appear as inline `# NOTE: ... (grammar gap)` comments.

The XSD itself remains the canonical conformance check. The builder
grammar is an ergonomic aid: it documents the schema, validates tag
placement and cardinality, and helps editors / type checkers, but
final XSD conformance must be validated separately against the
source schema.

## Bundled example

- `examples/fatturapa/` — Italian PA electronic invoice
  (`Schema_VFPA12_V1.2.3.xsd`, target namespace
  `http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2`).
  Source XSD, generated `fatturapa_elements.py`, hand-written
  `builder.py` with `FatturaPABuilder` and
  `FatturaPABuilderHandler`.

## Codegen architecture

Three layers under `codegen/`:

- `model.py` — parser-neutral dataclasses (`NamespaceModel`,
  `ElementModel`, `ChildModel`, `AttributeModel`,
  `SimpleConstraint`, `NamespaceRef`).
- `backend.py` — `XmlschemaBackend` maps `xmlschema.XMLSchema` to
  the model. Other backends (RelaxNG, JSON Schema, ...) can plug in
  here without touching the generator.
- `generator.py` — `PythonGenerator` deterministically emits Python
  source from the model.
- `__main__.py` — the CLI entry point above.

The model intentionally preserves XSD constraints the builder
grammar cannot yet express, so a future grammar extension can pick
them up without re-running the parser.
