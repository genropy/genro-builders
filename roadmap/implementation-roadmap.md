# Implementation roadmap — open problem

**Version**: 0.1.0
**Last Updated**: 2026-05-12
**Status**: 🔴 DA REVISIONARE — Documento non ancora approvato.
This document is intentionally **not a plan**. It exposes the
problem and lists what is on the table; it does not pick an order
and does not record decisions. Treating any statement here as a
commitment would be a misuse.

This document is a companion to
[architecture-contract.md](architecture-contract.md) and
[data-architecture.md](data-architecture.md). The contract fixes
the architectural decisions; the data document fixes the data
model; this document only frames the question
"in which order do we reintroduce the features?".

---

## 1. The problem

`develop` is intentionally stripped down. The features that the
blueprint (v0.2.0) had explored — pointers, datapath, components
with expansion, sub-builders, data elements, reactivity,
multi-builder — are not back yet. The architectural contract is
fixed, the data model has a draft, but no feature has been
re-implemented under the new contract.

The features are **not independent**. Each one presupposes parts
of the others; each one influences how the others will look. The
order in which they are reintroduced shapes both the amount of
code written and the amount of code rewritten. The question is
how to navigate this graph.

---

## 2. The axes (the features in question)

Each axis is listed with what it is and what other axes it
touches. No ranking is implied.

### 2.1 Data

The path grammar, `handler.data`, `^pointer`, `datapath`,
`abs_datapath`, `get_relative_data` / `set_relative_data`. See
[data-architecture.md](data-architecture.md).

Touches: every other axis. Without a data layer, components cannot
iterate, data elements have no destination, reactivity has nothing
to observe, sub-builders cannot share state.

### 2.2 Sub-builders

`@subbuilder(OtherBuilder)`: a declared switch of active builder
on a sub-tree (decision 2 of the contract). HTML → SVG is the
typical case.

Touches: data (sub-builders share or do not share the parent's
data — open question); render (the renderer of the sub-tree is
the sub-builder's renderer).

### 2.3 Components

`@component`: a macro-like construct that produces a sub-tree at
build time, preserved opaque in source (decision 7 of the
contract). Includes the `main_tag` invariant and the single-root
rule.

Touches: data (components often parameterise on a datapath and
read pointers); data elements (a component frequently emits data
elements alongside element nodes); iterate (a component with
`iterate` replicates over data children).

### 2.4 Data elements

`data_setter`, `data_formula`, and any other `@data_element`. They
write to or install resolvers on the data store; they are
transparent in the built tree.

Touches: data (they are the writers); components (data elements
are commonly grouped inside a component); reactivity (data formulas
are pull-based but trigger reactive cascades when dependencies
change).

### 2.5 Reactivity

Change propagation: a write to `handler.data` causes the renderer
(or compiler) to re-emit output. Includes the dependency graph,
the subscriber, the dispatch, the throttling.

Touches: every other axis. It is a meta-layer over a working
system: it observes data, runs because of data, and re-renders the
output of the rest.

### 2.6 Multi-builder

An orchestrator above one or more handlers (decision 4 mentions
this as an explicit layer above the handler). Coordinates handlers
that share state via volumes.

Touches: data (cross-handler reads go through volumes); reactivity
(coordinated reactivity across handlers is the main reason to
have an orchestrator at all).

---

## 3. The structural questions

These are the questions that the order of reintroduction must
answer, one way or another. They are listed here without an
answer — picking the order *is* picking the answer.

### 3.1 Depth vs breadth

Do we close one axis end-to-end before starting the next, or do
we keep all axes open and grow them in thin parallel slices? The
two extremes have known costs:

- All-depth: each axis is designed against an incomplete picture
  of the system, because the other axes are not yet there to push
  back on the design. The blueprint v0.2.0 followed this path and
  decision 8 was later renegotiated.
- All-breadth: every axis touches the others continuously, so a
  thin slice at level N often forces rewriting earlier slices.
  The work-on-rebuild of May 1st can be read as a reaction to
  this kind of churn.

Any concrete order sits somewhere between the two extremes.

### 3.2 Foundational vs applicative vs meta

Some axes look like foundations (the data layer is referenced by
everything), some look like applicative layers built on top
(components, data elements, sub-builders), some look like
meta-layers that observe and coordinate (reactivity, multi-builder).
The question is whether this layering is real or apparent: a
foundation that is too rigid forces rewrites above; a meta-layer
that comes too early has nothing stable to observe.

### 3.3 Where does the design pressure come from?

Each axis has different sources of design pressure. Data has the
pressure of "the grammar must compose"; components have "the
expansion must be predictable and re-runnable"; reactivity has
"the dispatch must be coalescing and idempotent". An axis
designed in isolation lacks the pressure from the other axes,
and the design that emerges may not survive contact with them.

### 3.4 What is the smallest end-to-end demo worth?

At some point the system has to produce a runnable example —
something more than the current `01_introduction` and
`02_inline_styling`. The minimum end-to-end demo that exercises
the data layer (for example: an invoice page that reads
`handler.data`) is itself a design constraint, because reaching
it requires a coherent slice across multiple axes. How early
that demo should be runnable is itself part of the order
question.

---

## 4. The dependency hints (not a graph, just observations)

A few observations about which axis presupposes which, drawn from
the data document and the contract. They are not a recipe.

- The data layer is referenced (as path grammar) by every other
  axis. It is the most-depended-on.
- Sub-builders and components are largely orthogonal to each
  other, but both touch the data layer.
- Data elements are values of the data layer and are commonly
  emitted from components; they sit between the two.
- Reactivity presupposes that data exists, that the renderer
  runs, and that the chain renderer → output is stable.
- Multi-builder presupposes everything that a single handler has,
  plus a coordination story.

These are dependency hints, not a layering verdict. Which axis
"comes first" is the open question.

---

## 5. Cost asymmetries to keep in mind

The cost of getting the order wrong is not symmetric across the
axes.

- **Rewriting the data layer late** is the most expensive. Every
  other axis embeds the path grammar in its code (`^x`, `^.x`,
  `^vol:x`, `#id`), so a grammar change ripples everywhere.
- **Rewriting reactivity** is contained: reactivity is mostly
  additive (subscriber + dispatch), so building it on a system
  that later changes shape is unpleasant but feasible.
- **Rewriting components / data elements / sub-builders** is
  intermediate: their public API leaks into user code (decorators,
  signatures), and changes there mean user-visible churn.

This asymmetry is one input to the order question; not the only
one.

---

## 6. What this document is not

- Not a plan: no axis is scheduled, no dependency is fixed.
- Not a ranking: the order of the axes inside §2 is the order they
  were named in the conversation, nothing more.
- Not a commitment: any sentence here is a frame for discussion,
  not a decision.
- Not a substitute for the contract or the data document: those
  two record the decisions that have been made.

The document exists so that the question "in which order do we
reintroduce the features?" can be discussed against a shared
picture of the axes and their interactions, without forcing the
answer.

---

## 7. Open items to address before deciding

A non-exhaustive list of open items whose resolution will inform
the order:

- The data layer in [data-architecture.md](data-architecture.md)
  is itself a draft (status 🔴): some sections will move from
  draft to fixed before they can be implemented.
- The behaviour of sub-builders with respect to data
  (shared `handler.data` vs sub-builder-local store) is mentioned
  as fixed in the data document, but no implementation exists
  yet, so the choice is reversible until it lands.
- The shape of the orchestrator (multi-builder) is only sketched
  in decision 4 of the contract. Its API surface is not specified.
- The reactivity dispatch model existed in the blueprint
  (`ReactiveManager`, `DependencyGraph`) but is not directly
  portable: handler-centric reactivity may look different.
- Some axes have **no current implementation** on `develop` at
  all (e.g. reactivity, data elements); others have **legacy
  implementations** that were not realigned to the contract
  (e.g. `contrib/data/data_builder.py`). The starting point is
  not uniform across axes.

Each open item is a place where the conversation can pick up.

---

**End of document. This file is intentionally short. It will
grow as the conversation around the order develops, but
*decisions* will be recorded in the contract or in the data
document, not here.**
