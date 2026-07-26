# Render architecture — core and renderers

**Version**: 0.1.0
**Last Updated**: 2026-07-26
**Status**: 🔴 DA REVISIONARE
**Audience**: internal. Contributors working on the render subsystem or
writing a new dialect — especially an *object* dialect (widgets, live
objects) or a reactive layer outside this repo.

This document describes how rendering works and where the line falls
between what the **core** owns and what each **renderer** decides. It is
descriptive for the total render (which already honours the line) and
prescriptive for the partial render (which does not yet).

---

## 1. The principle

The core never knows what a rendered thing *is*. It walks the source
tree, asks the dialect's renderer to produce one object per node, and
hands the nested result back to the renderer to be assembled.

    core           →  which nodes, in what order, nested how
    rendered_item  →  what ONE object is
    finalize       →  how the objects are assembled and delivered

A string dialect returns strings and joins them; an object dialect
returns widgets and mounts them. The walk is identical.

This is why the walk must never collapse the result. The fragments the
walk carries are **nested lists of opaque objects** — the moment the
core does `"".join(...)` it has assumed the dialect is textual, and an
object dialect passing through that code is broken.

## 2. The total render

`BuilderBase.render(mode, target, validate, **opts)` — builder/base.py

1. resolves `renderer_<mode>` (a property: one renderer instance per
   render, `BLD.3`);
2. resolves the target, and if it is a `TargetWrapper` merges its
   `render_opts` under the call's own opts — the destination dictates
   the form of the delivery;
3. `renderer.render_children(renderer.preprocess(self.source), **opts)`;
4. raises if `renderer.incomplete` collected minimum-cardinality misses;
5. `renderer.finalize(result, effective_target, **opts)`.

`RendererBase.render(node, **opts)` is the per-node step of the walk:

- a **data-element** is transparent → `None` (absence of output is
  `None`, never `""`: the walk emits no strings);
- a **component** goes to `_render_component` (expansion, §4);
- otherwise: resolve the node's own dialect renderer via `get_render`,
  `_handle_meta` (tag, ns, render_attributes), `adapt_attrs`, recurse
  into children if the value is a `SourceBag`, then
  `renderer.rendered_item(node, item, ra, tag=tag, **opts)`.

**Dialect boundaries.** Every per-node phase belongs to the renderer of
*the node's own* builder, resolved per node through `get_render`. An
`<svg>` subtree inside HTML is interpreted by the SVG renderer
throughout; the host renderer never applies its own rules to
foreign-grammar nodes. R0 (the entry renderer) keeps only what is
document-wide: the walk, the sub-renderer cache, and `finalize`.

**The two extension points.**

| method | owns | overridden by |
|---|---|---|
| `rendered_item` | what one object is | every dialect |
| `finalize` | how objects are assembled and delivered | dialects whose result is not a joined string, or that need a document-level option |

`RendererBase.finalize` is the string default: joins the fragments and
consumes the target (`None` → return text; path → write file; `.write`
→ file-like; callable → invoke). `XmlRenderer` overrides it for
`doc_header`. An object dialect overrides it entirely — genro-textual's
`TextualRenderer.finalize` mounts widgets onto a mount point instead of
joining anything.

## 3. Object dialects: the join is not universal

`RendererBase.render_type` distinguishes string dialects from object
ones. The reference implementation of an object dialect is
genro-textual (`TextualRenderer`, `render_type = "object"`), which:

- returns real Textual widgets from `rendered_item`;
- composes children **in the widget constructor** (`textual_class(*children)`),
  because Textual requires children at construction, not mounted after;
- mounts in `finalize` (`mount_point.remove_children()` + `mount(*widgets)`).

Nothing in the walk changes. This is the proof that the line in §1 is
real and already load-bearing.

## 4. Components and expansion

A component node is a **named node in the source** (the clean recipe)
whose expansion is a render-time fact, thrown away after use. The body
receives a throw-away root and builds exactly one tree into it; the walk
then re-enters on that tree, so dialect dispatch, nested components and
sub-builders apply as usual.

Expansion nodes therefore have **no stable identity**: they reincarnate
at every render.

`render_expansion_block(node, label, **opts)` renders ONE block of a
component — the per-row unit. It lives on the renderer and its contract
is explicit: *same prep, same body, same registration as the walk — the
fragment cannot diverge from a full render.*

Two component models exist. Only the first is implemented in Python:

| | A — projective (`iterate`/`store`) | B — data-widget |
|---|---|---|
| nodes | N rows, expanded per render | 1 node |
| who redraws | the engine | the widget itself |
| subscription | on the component node (coarse) | the widget subscribes to the Bag |
| internal state | cannot have any | keeps it (expansion, selection) |
| in Python | yes | **no** |
| in genro-dom-js | yes (`iterate`, tested) | yes (`dataWidget` + `storeBag`) |

In model A the subscription is coarse (`CMP.7`: *coarse subscription,
fine resolution*) — nodes inside an expansion resolve their pointers but
never enter the pointer map; the component node is the only subscriber.
Fine-grained updates must therefore be **reconstructed** afterwards,
which is the origin of the whole derived-identity apparatus (§6).

In model B the subscriber and the redrawer are the same object, so no
reconstruction is needed. genro-dom-js keeps data-widgets **out** of the
pointer map deliberately: re-rendering one would reset its internal
state.

## 5. The partial render — where the line is broken

`BuilderHandler.live()` accumulates touched nodes and, on exit of the
outermost section, calls `BuilderBase.render_nodes(entries, target)` —
its only caller.

`render_nodes` does two separable jobs:

**(a) Which nodes changed** — deciding the work list. Translating the
optimizer's `kind`s into operations, lifting a component child to its
enclosing element, deduplicating, dropping what an ancestor's replace
already covers. This is dialect-neutral: it is about the source tree and
the event queue, nothing else.

**(b) What to do with each one** — and here the core stops being
neutral. Every branch has the same shape:

```python
base = node.attr.get("id") or self.target_id(node)          # ① identity
fragment = renderer.render_expansion_block(node, label)      # ② redo — neutral
if isinstance(fragment, list):
    fragment = "".join(fragment)                             # ③ collapse
patches.append({"id": ..., "op": "replace", "html": fragment})  # ④ package
```

Step ② is already correct: it goes through the renderer and returns
whatever the dialect produces. Steps ①, ③ and ④ are HTML-and-string
assumptions written into `BuilderBase`:

- ① `id` is an **HTML attribute name** read by the core, and
  `target_id` is a string serial — meaningful only to a target reachable
  by name;
- ③ `"".join` appears **five times** in `render_nodes`. The total render
  exiled the join into `finalize`; the partial render brought it back
  into the builder;
- ④ the patch vocabulary is DOM: keys `id`/`op`/`html`/`before`, ops
  `replace`/`insert`/`remove`/`text`/`attr`/`page`.

The seven branches (`cell`, `page`, `row_remove`, `row_replace`,
`row_insert`, `remove`, `insert`, `replace`) differ in *which* pieces
they redo and how they anchor, but all end in ③+④.

**Consequence.** An object dialect cannot use the partial render at all.
genro-textual does not even qualify: its target is not a `TargetWrapper`
with `accepts_partial`, so `render_nodes` returns immediately to a total
render. The reactive engine exists and the one object dialect cannot
reach it.

## 6. Identity: three regimes, one of them accidental

| target | natural identity | today |
|---|---|---|
| remote DOM, across a socket | **a string is forced** | `target_id` + `getElementById` |
| local DOM, same memory | object reference | `targetId` + `querySelector` (ported from Python) |
| live widget, same memory | object reference | nothing — total render only |

Only the first case *needs* a string. The identity apparatus is
therefore infrastructure of one deployment model, not of rendering.

**How `id` got into the core** (git, 11 June 2026, hours apart):

- `187928a` creates `target_id` and calls it, verbatim, *dialect-neutral
  … only the reactive HTML render emits it today* — a per-document
  serial, assigned at first emission, frozen on the object so no
  structural mutation can stale it. At this commit `render_nodes` uses
  **only** `self.target_id(node)`; `"id"` appears solely as a patch dict
  key.
- `da78146` adds, in one go, `runtime_attrs.pop("id")`,
  `attr.get("id") or target_id(...)` and `attr["id"] = composite`. The
  reason is stated: the author must be able to **seed** the identity
  chain — `rows_block.r2.1` instead of `n7.r2.1`. The channel chosen was
  the HTML attribute.
- 12 June: `326c380`, `fba3ec9`, `c41909d`, `0c27a7f` inherit the
  pattern into `render_nodes` and `data_handler`.

The derived form is `<base>.<row label>.<ordinal>`: base from the
component node, one label per store crossed, ordinal from the body's
build order (*the body is code, the rebuild is identical*), which is why
row addresses need no capture at delete time — *the address is
arithmetic*.

Note what model A picked without declaring it: a hybrid —
`base.label.ordinal` puts a datum label between two render coordinates,
inheriting the fragile half of both families, and needing an origin the
data does not supply. Hence `id`.

### 6.1 The legacy precedent: `_identifier`

Genropy solved the same question — *what identifies a row?* — and its
answer was: **the core does not decide; whoever owns the data declares
it.** Worth documenting because it is the one prior art that got the
placement right.

`gnr.GnrStoreBag._identifier` (`gnrjs/gnr_d11/js/gnrstores.js`) is a
property of the **store**, default `'#id'`, interpreted by
`getIdentity(item)` through a small grammar:

| value | identity of the row |
|---|---|
| `#id` | the node's internal `_id` (default) |
| `#k` | the node **label** |
| `#i` | the **position** among siblings |
| `#p` | the full path |
| `##` | the numeric path |
| `.xx` | the **child** `xx` of the node |
| `xx` | the **attribute** `xx` of the node — e.g. `_pkey` |

Three properties matter more than the list itself:

1. **It is declared next to the data, not in the render engine.** The
   store owns it; the widget reads it. Compare with `base.label.ordinal`,
   which is computed by the renderer and needs an origin nobody owns.
2. **It is configuration, never markup.** `genro_wdg.js` strips
   `_identifier` together with `_type` among the attributes *"used only
   for triggering rebuild"* — it is a parameter, and never reaches the
   DOM. This is exactly the status `id` does **not** have in our core.
3. **It is bidirectional.** `getIdentity(item)` goes down (which row is
   this?), `fetchItemByIdentity(request)` comes back up (which row is
   this identity?) by scanning the store and comparing `getIdentity`.
   Same declaration serves both directions — no second mapping to keep
   in sync.

**Two families, and the choice is not neutral.** `#k`, `.child` and an
attribute name identify **the datum** — they survive reordering,
insertion and deletion. `#i`, `#p`, `##` identify **the position** —
they go stale the moment the collection changes. `#id` sits apart: an
internal serial, the same job as our `target_id`.

The clearest evidence of why the distinction matters is
`mixin_selectionKeeper` (`genro_grid.js`): before a refresh the grid
saves the selected rows **as identities**, and afterwards restores them
with `selectByRowAttr(this._identifier, this.prevSelectedIdentifiers,
...)`. With a positional identity a reorder would restore the selection
onto the wrong records. The same reasoning applies to any state a user
holds across a refresh — expansion, scroll, focus.

**What was actually used.** In practice one mode: grids default to
`_pkey` (three separate call sites in `genro_components.js`), stores to
`#id`, one store declares `nodelabel`, the tree accepts an `identifier`
and falls back to `#id`. Across the whole legacy Python only
`bagStore()` in `gnrwebstruct/dojo11.py` exposes `_identifier` at all,
and it defaults to `None`.

So the flexibility was mostly unused — but that is not the lesson. The
lesson is the *default* (`_pkey`: the record key) and the *placement*
(on the store, declared by the author, invisible to the markup). The
seven forms were the escape hatch for collections without a key.

## 7. Where the line should fall

The test: **imagine ws-web never existed. Build the core clean. Then
build ws-web without the ability to touch this repo — at most, open an
issue.**

Today that test fails: `render_nodes` is a `BuilderBase` method, so an
external layer cannot supply its own.

The fix follows the shape already proven by the total render. The core
keeps (a) — which nodes changed — and delegates (b) to the renderer,
exactly as the walk delegates to `rendered_item` and the assembly to
`finalize`:

    render_nodes   (core)      →  which nodes changed, in what operation
    render_node    (renderer)  →  what to do with ONE changed node
    finalize       (renderer)  →  how the results are delivered

Then:

- the **static** renderer does not implement it → total render;
- a **ws** renderer produces `{"id","op","html"}`, owns `target_id`, the
  cell catalog, the derived identity, the lazy machinery, and joins its
  own strings in its own `finalize`;
- a **textual** renderer calls `widget.update(...)` on the live object;
- an **object/SQL** renderer does whatever a live object needs.

Because the branches are not all "one node, one fragment" — an insert
needs its anchor sibling, a remove acts on a node already gone — the
core must pass the operation and its context, not merely the node. The
exact signature is open; genro-textual's `doc-B-partial-render-queue.md`
proposes `(anchor, result)` items and leaves the same question open:
*is the anchor the SourceBagNode or a stable id? (the WS consumer wants
an id; the textual consumer wants the widget; the test consumer wants
the node)*. Its own answer — *anchor = node, and the node carries the
id* — is consistent with this document: the consumer chooses, the core
does not.

### One thing must move the other way

Row rules (`dataFormula`/`dataController` inside a component body) are
registered inside `_register_expansion_writeback`, which is gated by
`include_datapath`. They are **general reactivity**, not patch
machinery: today a static render does not register them at all. That
block belongs in the core, called unconditionally from `_expand_block`.

## 8. Sizing

Machinery that exists solely for the patch-based partial render, as of
this writing:

| file | total | patch-only | % |
|---|---|---|---|
| `builder/base.py` | 1453 | ~430 | ~30% |
| `renderer/base.py` | 831 | ~280 | ~34% |
| `builder/data_handler.py` | 1148 | ~320 | ~28% |

`render_nodes` alone is ~270 lines with one caller and one purpose.

Two structures — `_writeback_map` and `node_by_target_id` — are built by
the core and read by **nobody inside it**: their only consumers are the
application layer and the examples. The core populates them for someone
else.

---

## Riferimenti

Analisi condotta il 2026-07-25/26 su genro-builders (branch
`feat/closed-signature-rejects-undeclared`), con verifiche incrociate su
genro-ws-web, genro-dom-js (109 test verdi), genro-textual (fermo, non
importa contro il core attuale) e il legacy gnrjs.
Session-id: 6962ddd1-a3a9-4b94-8571-a279b59416a9.
