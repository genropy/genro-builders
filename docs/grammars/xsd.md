# XSD dialects

**Last Updated**: 2026-06-03
**Status**: 🟢 APPROVATO — `XsdBuilderBase`/`XsdHandler` + two-class codegen landed 2026-06-03.
**Maintainer**: core team.

XSD support is a **codegen** pipeline plus two light base classes. Given
an XSD schema, the codegen writes a self-contained Python module — a
`<Dialect>Builder` + `<Dialect>Handler` pair — that you commit and import
with no runtime dependency on the parser. On-the-wire format is XML.

## Purpose

Turn an XML Schema into an ergonomic, validated builder grammar: one
`@element` per schema element, cardinalities as `sub_tags`, enumerations
as `Literal`, bounded/patterned simple types as `Annotated[...]`. The
schema itself remains the canonical conformance check — the grammar is an
authoring aid (documents the schema, validates tag placement, helps
editors), not a full XSD validator.

## The two bases

```python
from genro_builders.contrib.xsd.xsd_builder import XsdBuilderBase, XsdHandler
```

- `XsdBuilderBase(BuilderBase)` — grammar base for XSD-born dialects;
  default render mode is `xml`.
- `XsdHandler(BuilderHandler)` — engine preset; a concrete handler binds
  `builder_class`.

The XML render is the core's real `XmlRenderer` (pointers resolved,
framework markers filtered) — see [HTML grammar](html.md) for the `xml`
mode vs. the raw `source.to_xml()` view.

## Quick start — bundled Sitemap example

```python
from decimal import Decimal

from genro_builders.contrib.xsd.examples.sitemap import SitemapHandler


class MySitemap(SitemapHandler):
    def main(self, root):
        s = root.urlset()
        home = s.url()
        home.loc("https://www.example.com/")
        home.changefreq("daily")
        home.priority(Decimal("1.0"))


sm = MySitemap()
sm.create()
print(sm.render(mode="xml", pretty=True))
```

Output:

```xml
<urlset>
  <url>
    <loc>https://www.example.com/</loc>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
</urlset>
```

## Generating a dialect

```bash
python -m genro_builders.contrib.xsd.codegen \
    --xsd path/to/schema.xsd \
    --dialect-name MySchema \
    --output path/to/my_schema.py
```

Requires the `[xsd]` extra (`xmlschema`), needed **only** to run the
codegen. The generated module imports neither `xmlschema` nor the codegen.

## A starting base, to refine

The codegen emits as builder grammar:

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

- `examples/sitemap/` — small schema modelled on the public Sitemaps
  protocol 0.9 (`urlset`/`url`, `changefreq` enum, `priority` range).
- `examples/fatturapa/` — Italian PA electronic invoice
  (`Schema_VFPA12_V1.2.3.xsd`); large real-world schema, several patterns
  commented out per the rule above.
