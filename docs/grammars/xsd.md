# XSD dialects

**Last Updated**: 2026-07-27
**Status**: 🟢 APPROVATO — allineato al contratto v0.9.0 (XML core +
builder-only codegen).
**Maintainer**: core team.

XSD support is a **codegen** pipeline (the transpiler) plus a light
grammar base. Given an XSD schema, the transpiler writes a
self-contained Python module — a `<Dialect>Builder` — that you commit
and import with no runtime dependency on the parser. On-the-wire
format is XML.

## Purpose

Turn an XML Schema into an ergonomic, validated builder grammar: one
`@element` per schema element, cardinalities as `sub_tags`, enumerations
as `Literal`, bounded/patterned simple types as `Annotated[...]`. The
schema itself remains the canonical conformance check — the grammar is an
authoring aid (documents the schema, validates tag placement, helps
editors), not a full XSD validator. The pre-render cardinality check
(contract `PAG.4`) is the structural first net.

## The grammar base

```python
from genro_builders.xml import XmlBuilderBase
```

`XmlBuilderBase(BuilderBase)` — shared grammar base for the
XML-on-the-wire dialects (XSLT and the schema-generated ones); default
render mode is `xml`. The namespace-tag mechanism (`_meta`
`ns`/`local`, `xmlns_<prefix>` attributes) lives on the core
`XmlRenderer`. A generated dialect is an ordinary builder: subclass it
for a page, or use it directly like any other.

The XML render is the core's real `XmlRenderer` (pointers resolved,
framework markers filtered) — see [HTML grammar](html.md) for the `xml`
mode vs. the raw `source.to_xml()` view.

## Quick start — bundled Sitemap example

```python
from decimal import Decimal

from genro_builders.xml.examples.sitemap import SitemapBuilder


class MySitemap(SitemapBuilder):
    def main(self, root):
        s = root.urlset()
        home = s.url()
        home.loc("https://www.example.com/")
        home.changefreq("daily")
        home.priority(Decimal("1.0"))


sm = MySitemap()
sm.create()
print(sm.render(pretty=True))
```

## Generating a dialect

```bash
python -m genro_builders.xml.transpiler \
    --xsd path/to/schema.xsd \
    --dialect-name MySchema \
    --output path/to/my_schema.py
```

Requires the `[xsd]` extra (`xmlschema`), needed **only** to run the
transpiler. The generated module imports neither `xmlschema` nor the
transpiler.

## A starting base, to refine

The transpiler emits as builder grammar:

- one `@element` per element (global + locally declared);
- `sub_tags='a[1],b[0:],c[1:5]'` with explicit cardinalities;
- attributes / `simpleContent` as call-args, with `Literal[...]` for
  enumerations and `Annotated[..., Regex(...)]` / `Annotated[..., Range(...)]`
  for pattern / `minInclusive` / `maxInclusive` facets.

It does **not** silently swallow what it cannot express — it surfaces it as
`# NOTE:` comments for the developer to refine by hand:

- `minLength`/`maxLength`/`totalDigits`/`fractionDigits` (grammar gaps);
- XSD patterns Python's `re` cannot compile — most notably Unicode *block*
  properties (`\p{IsBasicLatin}`, XML Schema / Java / .NET syntax). The
  validator is emitted **commented out**, so construction never raises on a
  pattern `re` would reject; the original pattern stays in the comment.

## Bundled examples

Under `src/genro_builders/xml/examples/`:

- `sitemap/` — small schema modelled on the public Sitemaps
  protocol 0.9 (`urlset`/`url`, `changefreq` enum, `priority` range).
- `fatturapa/` — Italian PA electronic invoice
  (`Schema_VFPA12_V1.2.3.xsd`); large real-world schema, several patterns
  commented out per the rule above.
