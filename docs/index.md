# genro-builders

**Version**: 0.1.0
**Last Updated**: 2026-05-14
**Status**: 🔴 DA REVISIONARE — Documento non ancora approvato.

Builder system for [genro-bag](https://github.com/genropy/genro-bag).
Construct structured documents — HTML, SVG, CSS — through a fluent,
validated Python API.

## What ships today

Three working grammars under `genro_builders.contrib`:

| Grammar | Module | Notes |
|---------|--------|-------|
| HTML5 | `genro_builders.contrib.html` | 112 elements from the W3C schema |
| SVG | `genro_builders.contrib.svg` | 56 elements |
| CSS | `genro_builders.contrib.css` | Level 1 (rules, selectors, vars, `@media`/`@supports`/`@import`) |

Two more grammars are under realignment to the current contract and
not currently usable: `contrib.xsd`, `contrib.data`.

## Where to start

- **[Getting started](getting-started.md)** — first page in 5 minutes.
- **[Builders overview](builders/overview.md)** — what a builder is,
  how the lifecycle works.
- **[Decorators](builders/decorators.md)** — `@element`, `@abstract`,
  `@subbuilder`, `@component`, `@data_element`.
- **[Common patterns](builders/patterns.md)** — `._` chaining,
  `node_by_id`, `render_target`.
- **Grammars** — per-grammar reference:
  [HTML](grammars/html.md), [SVG](grammars/svg.md),
  [CSS](grammars/css.md).

## In-flight design

Documents describing where the project is heading — not yet shipped
in code — live in `roadmap/` at the repo root:

- `roadmap/architecture-contract.md` — the 12 architectural decisions.
- `roadmap/data-architecture.md` — the data model proposal (pointers,
  datapath, volumes).
- `roadmap/implementation-roadmap.md` — open problem framing.
- `roadmap/documentation-guide.md` — how to write docs.
- `roadmap/history.md` — project timeline.

## Status of the current scaffold

This documentation skeleton describes the framework as it exists
**today**. Features still under design (data pointers, reactivity,
multi-handler orchestrators) are not documented here — they live in
`roadmap/` and will move to `docs/` when they ship.

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
