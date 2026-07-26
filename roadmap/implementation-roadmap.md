# Implementation roadmap — open work

**Last Updated**: 2026-06-10
**Status**: 🟡 DA RIALLINEARE al contratto v0.9.0.

> **Stato dopo il contratto v0.9.0 (2026-07-26).** Le voci sulla
> reattività push (Livello 0, `live()`, render parziale nel flush,
> granularità SRC/DATA) non sono più "lavoro aperto" in Python: quel
> codice è uscito e la reattività fine si rifonda sulla compiled bag
> (`RX.5`), che è **ricerca con documento proprio**. Restano aperte, e
> invariate, le voci non reattive: `@container` (`CMP.9`),
> `<domain>requires`/`include_components` (`CMP.6`), `@slot` (`PAG.6`),
> `format` v2, `from_grammar`, e la formalizzazione di `APP`.
This document is intentionally **not a plan**. It maps what is open
and how the open pieces depend on each other; it does not pick an
order and does not record decisions. Decisions live in
[architecture-contract.md](architecture-contract.md).

---

## 1. Where the rebuild stands

The reintroduction question that this document used to frame ("in
which order do we bring the blueprint features back?") is largely
answered: the axes are back on `develop` under the v0.8.0 contract.

Closed axes:

- **Data (pull-based)** — path grammar, `^`/`=` pointers, `${}`
  templates with consumed inputs, `mask`/`_wdg` presentation,
  read-time pointer registration (`DAT.2`, `DAT.5`, `DAT.6`).
- **Sub-builders** — `@subbuilder` with handler propagation and
  literal boundary envelopes (`BLD.2`).
- **Render subsystem** — universal walk, per-node dialect dispatch,
  fused `finalize`, pre-render cardinality minima (`RND`, `PAG.4`).
- **Data elements** — `data_setter`/`data_formula`/`data_controller`
  as marked `@element`, compute slice 1 (`DAT.3`, `DAT.4`).
- **Multi-builder** — the suite-level orchestrator dissolved into the
  multibuilder `BuilderHandler` (`HND.1`): N builders mounted by name
  on one segmented datastore.
- **Push reactivity Level 0** — `live()` as the handler's mutation
  critical section, per-mount render queue, forbidden without an
  application (`RX.1`).

Components are **back as a design** (`CMP`, full record in
[component-design.md](component-design.md)): named node in the
source, ephemeral render-time expansion, `iterate`/`value`. The
2026-04-27 drop decision is superseded; the code is not written yet.

## 2. The open axes

### 2.1 Component (`CMP`) + `@slot` (`PAG.6`)

The largest unimplemented design. Component: decorator, render-walk
third branch, iterate/label mechanics, fractal composition tests.
Slot: fill-by-id at node birth (the ws_live frame with header/footer
panels is the guide case). Leftovers to reconcile while implementing:
the surviving `@component`/`include_components` from June 6, the
`pyrequires` successor (`<domain>requires` family), the
`test_no_components_section_post_v0_4_0` sentinel test.

### 2.2 Data-element cascade (slice 2, `DAT.4`)

Multi-wave compute: FIFO breadth-first queue, anti-loop (per-node
input dict + run-count backstop). Slice 1 (single wave) is in.

### 2.3 Reactivity granularity (`RX`)

Partial render in the `live()` flush (`render_nodes` per touched
node, `_optimize_render` reduction), SRC/DATA dispatcher separation,
component reactivity by path arithmetic (`CMP.7`), variable datapath
/ master-detail (see
[reactivity/variable-datapath.md](reactivity/variable-datapath.md)).

### 2.4 Application (`APP`)

The world↔handler layer. `contrib/ws_live` is the living reference;
the area is formalized when it stabilizes (API, hooks,
multi-session).

### 2.5 Cross-runtime

"One language, two interpreters": the semantic contract of the
source, the JS twin (bag/builder client-side), golden tests (same
recipe + same mutations → same tree). Far horizon; constrains design
today (named components, func-by-name).

## 3. Dependency hints

- CMP needs nothing new from the data layer (read-time registration
  already serves ephemeral nodes); its reactive half (CMP.7) lands
  with RX granularity, not before.
- Slice 2 and RX granularity are independent of CMP but share the
  queue/anti-loop machinery: whichever lands first shapes the other.
- APP formalization gates nothing: ws_live evolves freely; the
  contract area is descriptive.
- Downstream conversions (genro-textual, genro-print, genro-scriba)
  consume the current model and put real-world pressure on PAG/HND;
  they inform the preset question (open in the contract).

## 4. What this document is not

- Not a plan: no axis is scheduled.
- Not a commitment: any sentence here frames discussion.
- Not a substitute for the contract: decisions are recorded there
  (or in component-design.md for the component record).
