# XsdBuilder

Dynamic XML builder generated from XSD (XML Schema Definition) files at runtime.
Parses an XSD schema and creates a fully validated builder with elements,
types, and cardinality constraints.

## Install

```bash
pip install genro-builders
```

## Quick start

```python
from genro_builders import BuilderBag
from genro_builders.contrib.xsd import XsdBuilder

bag = BuilderBag(builder=XsdBuilder, builder_xsd_source='schema.xsd')
doc = bag.Document()
# ... build document following XSD structure ...

bag.builder.build()
xml = bag.builder.render()
```

## XsdReader

For low-level XSD parsing without building a full builder:

```python
from genro_builders.contrib.xsd import XsdReader

reader = XsdReader('schema.xsd')
for element in reader:
    print(element.name, element.children)
```

## Examples

See [examples/](examples/) for complete working examples:

- **sepa_payment.py** — SEPA payment XML generation from XSD
- **demo_payment.py** — Demo payment using the SEPA builder

## Documentation

Full documentation: [docs/builders/xsd-builder.md](../../../../docs/builders/xsd-builder.md)
