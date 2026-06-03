# genro-builders

**Last Updated**: 2026-06-02
**Status**: 🟢 APPROVATO — allineato al contratto v0.7.0.

Builder system for [genro-bag](https://github.com/genropy/genro-bag).
Construct structured documents — HTML, SVG, CSS — through a fluent,
validated Python API.

## What ships today

Four working dialects under `genro_builders.contrib`:

| Grammar | Module | Notes |
|---------|--------|-------|
| HTML5 | `genro_builders.contrib.html` | 112 elements from the W3C schema |
| SVG | `genro_builders.contrib.svg` | 60+ elements |
| CSS | `genro_builders.contrib.css` | Level 1 (rules, selectors, vars, `@media`/`@supports`/`@import`) |
| XSD | `genro_builders.contrib.xsd` | `XsdBuilderBase`/`XsdHandler` + codegen pipeline; bundled Sitemap and FatturaPA example dialects |

`contrib.data` exposes `DataBuilder`, a schema-only builder used as
infrastructure by the data layer; it has no renderer and is not a
user-facing dialect.

## Where to start

- **[Getting started](getting-started.md)** — first page in 5 minutes.
- **[Builders overview](builders/overview.md)** — what a builder is,
  how the lifecycle works.
- **[Decorators](builders/decorators.md)** — `@element`, `@abstract`,
  `@subbuilder`, and the data-elements.
- **[Common patterns](builders/patterns.md)** — `._` chaining,
  `node_by_id`, render targets.
- **Grammars** — per-grammar reference:
  [HTML](grammars/html.md), [SVG](grammars/svg.md),
  [CSS](grammars/css.md), [XSD dialects](grammars/xsd.md).

## In-flight design

Documents describing where the project is heading — not yet shipped
in code — live in `roadmap/` at the repo root:

- `roadmap/architecture-contract.md` — the architectural contract
  (v0.7.0, in vigore dal 2026-06-02).
- `roadmap/data-architecture.md` — the data model proposal (pointers,
  datapath, volumes).
- `roadmap/implementation-roadmap.md` — open problem framing.
- `roadmap/documentation-guide.md` — how to write docs.
- `roadmap/history.md` — project timeline.

## Status of the current scaffold

This documentation skeleton describes the framework as it exists
**today**: pull-based binding (`DAT.2`), data-elements with their
compute (`DAT.4`), and push reactivity Level 0 (`handler.live`,
`RX.1`). Features still under design — the data-element cascade
(slice 2), finer-grained reactivity, multi-handler orchestration —
are not documented here: they live in `roadmap/` and will move to
`docs/` when they ship.

```{toctree}
:hidden:
:caption: Getting started

getting-started
```

```{toctree}
:hidden:
:caption: Builders

builders/overview
builders/decorators
builders/patterns
```

```{toctree}
:hidden:
:caption: Grammars

grammars/html
grammars/svg
grammars/css
```
