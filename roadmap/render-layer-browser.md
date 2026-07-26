# Layer 3 — reactive in the browser

**Version**: 0.1.0
**Last Updated**: 2026-07-26
**Status**: 🔴 DA REVISIONARE
**Parent**: [render-architecture.md](render-architecture.md)
**Implementation**: `genro-dom-js` (JS port, 109 tests green)

> **Status after contract v0.9.0 (2026-07-26).** This layer becomes the
> **primary direction**, not one option of three: for HTML with a JS
> renderer Python needs no reactivity of its own, because the compiled bag
> already lives on this side of the wire (the DOM over `bag-js`), where the
> nodes are real by nature. The Python half of the bridge is `RX.5`.

The layer where the recipe is shipped once and everything else happens
client-side. It is the traditional Genropy model — most of the GUI logic
in JS — rebuilt on the builders' architecture.

Its interest here is not the port itself but what it **proves about the
core**: which parts of the reactive machinery are essential and which
are artefacts of the server-side deployment.

---

## 1. The deployment model

Two input channels, one engine:

- a **native JS page** — a class extending `HtmlBuilder` with a `main()`;
- a **recipe imported from Python** — genro-builders on the server
  produces the source Bag, serializes it, the browser renders it.

Either way the renderer and the reactive engine only ever see a source
Bag; they cannot tell where it came from. After that first delivery the
recipe does not change and the data lives in the browser: **nothing
crosses the wire again**. `setItem` → patch is synchronous inside
`live()`.

The renderer builds **real DOM nodes — not strings, not a virtual
tree** — so the fragments the walk carries are `Element` objects and
`finalize` composes a `DocumentFragment` instead of joining. This is the
`DIFF-PYTHON` the port documents explicitly, and it is the same
divergence an object dialect has (see genro-textual).

## 2. What it proves

**The whole model A machinery works unchanged.** `iterate`, per-row
expansion, derived identity, cell patches, writeback map: all ported,
109 tests green. So the projective component model is not tied to the
server.

**But it also inherited what it did not need.** `targetId` (`n1`, `n2`,
…) is assigned exactly as in Python, stamped as `element.id`, and
patches are applied with `querySelector('[id="..."]')`. There is no
`WeakMap`, no `domNode` slot — the object reference is available in the
same memory and the port throws it away, then buys it back with a DOM
query.

This is the sharpest evidence in the whole analysis: **the string
identity is not a requirement of reactivity, it is a requirement of
serialization.** Where serialization is absent it survives only as
inheritance. The port's own doc says the engine patches *"directly onto
the bound DOM nodes"* — the implementation does not match the model it
describes.

The defect travelled too: `compNode.getAttr('id') || builder.targetId(compNode)`
is in the JS renderer, verbatim. Fixing `id` in Python without deciding
for both rails leaves them divergent.

## 3. The second component model — the part Python lacks

This layer has something the Python core does not: **data-widgets**.

```js
pane.storeTree({ store: '^data.folders', labelAttribute: 'caption' })
```

A `storeTree` is a **single node** marked `dataWidget`. The renderer
hands it the resolved Bag branch as a JS property — `el.storeBag = bag`,
an object, never a stringified attribute — and the widget owns
everything from there: it draws the hierarchy, keeps its own
expand/collapse state, and subscribes to the Bag to redraw on change.

Crucially it is **kept out of the pointer map**, with the reason stated
in the code: the engine would otherwise re-render it on every change
under the branch and *reset its internal state*.

| | A — projective (`iterate`) | B — data-widget |
|---|---|---|
| nodes | N rows, reincarnating | 1 |
| identity | derived `base.label.ordinal` | the object itself |
| who redraws | the engine, by patch | the widget, by subscription |
| internal state | impossible | preserved |
| needs `id` | yes, for the base | no |

**The two must coexist.** Some components are macro-widgets (tree, grid:
they own a collection and its presentation); others are traditional
components (a row body expanded per record). Model B is not a
replacement — it is the right answer for a different kind of component.

What is missing in Python is the *declaration*: the core knows `store`
only as a synonym of `iterate` for anchoring a collection to the
projective model (`node.attr.get("iterate") or node.attr.get("store")`).
There is no way to say "this component owns its collection, leave it
alone". `data_widget` does not exist in the Python core.

Note also that model B answers the identity question by dissolving it:
no rows to name, no base to seed, no writeback entries. The apparatus
disappears with the problem it solved.

## 4. What this layer needs from the core

Nothing that layer 2 does not also need, plus one thing:

1. the queue of what changed, with the anchor as **node** (this layer
   can reach the DOM element from it; layer 2 needs to derive a string,
   and that derivation is layer 2's business);
2. `render(startnode=...)` returning a self-contained fragment — here an
   `Element`, there a string: the core must not care;
3. **a way to mark a component as model B**, so the engine keeps it out
   of the pointer map and hands it the resolved branch instead of
   expanding it. This is the one genuinely missing core capability, and
   it is small: a `_meta` marker plus the pointer-map exclusion.

Requirement (3) is what an issue against `genro-builders` should ask
for. Requirements (1) and (2) it shares with layer 2.

## 5. Known weaknesses of the current port

- **`nodeByTargetId` is a linear walk with no index.** One scan per
  write-back; with `updateOn: 'input'` that is a scan per keystroke on a
  page-sized tree.
- **It inherited `id`** (§2) — same fix as layer 2, and the two should
  be decided together.
- **The patch payload is an `Element`**, so this layer's patches are by
  definition local and not serializable. The exception is `text`/`attr`
  patches, which are already pure strings — the one place where the two
  layers coincide completely.

## 6. Relationship with the other layers

| | layer 1 static | layer 2 WS | layer 3 browser |
|---|---|---|---|
| where the recipe lives | server | server | shipped once, then client |
| where the data lives | — | server | client |
| what crosses the wire | the document | patches, continuously | the recipe, once |
| target reachable by reference | n/a | **no** | yes |
| identity needed | none | forced, string | none (inherited anyway) |
| component models | A | A | A + B |

Layer 3 does not replace layer 2: they answer different questions about
where the logic should live. The point of layer 2 was to measure what a
Python-only stack with a passive HTML client costs; the cost, measured,
is the ~1030 lines catalogued in the parent document and the pressure
they put on the core.

---

## Riferimenti

Session-id: 6962ddd1-a3a9-4b94-8571-a279b59416a9.
