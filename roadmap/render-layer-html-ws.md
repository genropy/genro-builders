# Layer 2 — reactive HTML over WebSocket

**Version**: 0.1.0
**Last Updated**: 2026-07-26
**Status**: 🔴 DA REVISIONARE
**Parent**: [render-architecture.md](render-architecture.md)

> **Status after contract v0.9.0 (2026-07-26).** The machinery described
> here **no longer exists in genro-builders**: it was removed and
> deposited verbatim in `genro-ws-web@c88c6e6`
> (`attic/partial-render/`). This document stays valid as the **rebuild
> spec for that deposit**, and NOT as a specification for Python. What
> replaces it is not a repair of this design but a different one: a
> compiled bag emitted by a `livehtml` render mode, with the wire
> carrying **bag mutations** (`ins`/`upd`/`del` on a path) instead of DOM
> ops (`RX.5`). Whoever rebuilds this should read `CMP.7` first, to see
> why the identity apparatus described below was a surrogate.

The layer that keeps everything in Python and sends the browser a stream
of patches. This document exists so it can be **rebuilt from outside**
`genro-builders` — the test being: *imagine ws-web never existed; build
the core clean; then build this without touching the builders repo, at
most opening an issue.*

Today most of it lives in the core and would fail that test. What
follows is both a description of the mechanism and a specification for
where each piece belongs.

---

## 1. The deployment model

Source tree, data and rendering all live in Python. The browser holds
only the resulting DOM and a thin client (450 lines of JS in ws-web).
Nothing about the page's structure or logic exists client-side.

The consequence that shapes everything: **the render target is
unreachable except by name.** The producer of an update and the thing
being updated are in different processes. A string identity is therefore
not a design choice, it is forced.

This is what makes this layer's machinery *its own* and not the core's:
no other layer has this constraint.

## 2. The identity bridge

One namespace of ids, used in both directions — patches go down
addressed by it, mutations come up addressed by it.

Three origins:

| origin | form | for |
|---|---|---|
| serial | `n1`, `n2`, … | stable source nodes |
| derived | `<base>.<row label>[.<label>].<ordinal>` | expansion nodes, which reincarnate |
| author's | whatever the author wrote | seeds the derived chain |

- **Serial** — assigned lazily at first emission from a per-document
  counter, frozen on the node, never recomputed: bound to the object, so
  no structural mutation can stale it. Emitted on *every* element,
  because any element may become a patch target, a container or an
  anchor at runtime.
- **Derived** — expansion nodes get no serial (they reincarnate). Their
  address is computed: base from the component node, one label per store
  crossed, ordinal from the body's build order. *The body is code, the
  rebuild is identical* — which is why a deleted row needs no id capture:
  the address is arithmetic.
- **Author's** — today read from the HTML attribute `id`. **This is the
  defect.** See §6.

Upstream half: `node_by_target_id` (walk over the source, comparing the
slot) for serials, `_writeback_map` (flat dict) for derived ids. The
mutation lane consults the map first, then falls back to the walk.

## 3. The wire

Patches are dicts. Six ops, all DOM:

| op | payload | client |
|---|---|---|
| `replace` | `id`, `html` | `getElementById` + morph |
| `insert` | `id` (container), `before` (sibling id), `html` | `insertAdjacentHTML` |
| `remove` | `id` | `el.remove()` |
| `text` | `id`, `value` | `el.textContent = value` |
| `attr` | `id`, `name`, `value` | `setAttribute` |
| `page` | `id`, `page`, `html` | lazy placeholder fill |

The client resolves every op with `document.getElementById(patch.id)` —
no client-side map: **the DOM is the registry**. The morph uses the same
ids as matching keys, so the diff is identity-driven rather than
heuristic; that only works because the reactive render puts an id on
every element.

Upstream, the client sends `{page, id, value?}` and nothing else. Path
and dtype never travel: the server resolves the node by identity and
reads them *there*. Writes to an arbitrary path, and dtype injection,
do not exist as categories.

## 4. Granularity and its cost

The subscription is coarse (`CMP.7`: the component node subscribes, the
nodes inside an expansion do not) but the update must be fine, or every
cell change would redraw the whole block. Bridging the two is what the
machinery does:

- `_expansion_row` decodes a mutated path into `(kind, row label,
  field)` — `cell_upd` / `row_ins` / `row_del` / `row_upd`;
- `_cell_map` catalogues, per component, which ordinal shows which
  field — built once per expansion because the body is code and every
  row has the same shape;
- density thresholds collapse fine into coarse: `CELLS_PER_ROW_LIMIT`
  (4) → row replace, `ROW_COALESCE_LIMIT` (50) → container replace.

**Lazy iterate** is a further refinement of the same lane: park the
collection, deliver page 0 plus a marker carrying the total, let the
client fabricate placeholders and ask for pages as the scroll demands
(`lazy_park`, `lazy_page`, `_lazy_transit`, `render_lazy_page`, the
`<base>.lazy` marker, the `page` op). Roughly 240 lines, entirely this
layer's.

## 5. Where it lives today, where it belongs

| piece | today | belongs |
|---|---|---|
| `render_nodes` — which nodes changed | `BuilderBase` | **core** (keep) |
| `render_nodes` — patch production | `BuilderBase` | this layer |
| `target_id`, `node_by_target_id`, `_target_serial` | `BuilderBase` | this layer |
| `_writeback_map`, `_writeback_add`, `_purge_writeback_prefix` | `BuilderBase` | this layer |
| `_register_expansion_writeback` (identity part) | `RendererBase` | this layer |
| `_register_expansion_writeback` (row rules) | `RendererBase`, gated | **core**, ungated |
| `_register_cell`, `_cell_map` | `RendererBase` | this layer |
| lazy machinery | renderer + handler | this layer |
| `_expansion_row`, density thresholds | `BuilderHandler` | this layer |
| `_auto_id_attr`, `data-*-pointer` emission | `HtmlRenderer` | this layer |
| `render_expansion_block` | `RendererBase` | **core** (neutral, already correct) |
| `accepts_partial`, `partial()`, `render_opts` | `TargetWrapper` | this layer |

Two structures — `_writeback_map` and `node_by_target_id` — are built by
the core and read by **nobody inside it**. Their only consumers are the
application layer and the examples.

## 6. The three defects to fix on rebuild

**`id` is read by the core.** `node.attr.get("id") or target_id(node)`
appears in `render_nodes` (4×), `_render_lazy_component`,
`render_lazy_page`, `_register_expansion_writeback` (which also *writes*
`attr["id"] = composite`), `_register_cell`, `_lazy_row_delivered`.
`id` is an HTML word; a configuration or SQL grammar has no use for it,
yet inherits it. On rebuild the seed must have a name of this layer's
own, projected onto the HTML attribute by the HTML renderer — the same
relation `class_` → `class` already has.

**The join is back in the builder.** `"".join(fragment)` appears **five
times** in `render_nodes`. The total render exiled it into `finalize`;
the partial render brought it back. Any object dialect passing through
that code is broken. On rebuild the collapse belongs in this layer's
`finalize`.

**The patch vocabulary is in the core.** `{"id", "op", "html"}` and the
six ops are written into `BuilderBase.render_nodes`. They are this
layer's protocol and should be produced by this layer's renderer.

## 7. Rebuild specification

What this layer needs from a clean core:

1. **a queue of what changed** — the entries `live()` accumulates, with
   enough context per entry (operation kind, row label, field) to decide
   granularity. Whether the anchor is the node or an id is the core's
   choice; the node is preferable, the consumer derives the rest;
2. **`render(startnode=...)`** producing a self-contained fragment —
   `render_expansion_block` and `renderer.render(container)` already do
   this and are neutral;
3. **a place to hang its own state** — the identity maps, the cell
   catalogue, the lazy parking are this layer's, and the core must not
   know them;
4. **`rendered_item` / `finalize` overridable** — already true.

What this layer supplies for itself: identity (serials, derived
addresses, the author seed under its own name), the patch vocabulary,
the cell catalogue, the density thresholds, the lazy lane, the
`TargetWrapper` with `accepts_partial`, and the JS client.

If the core cannot supply (1) and (2) without modification, that is what
an issue asks for — not a patch to `BuilderBase`.

## 8. Sizing

~1030 lines across `builder/base.py`, `renderer/base.py` and
`builder/data_handler.py` — about 30% of those three files.
`render_nodes` alone is ~270 lines, one caller, one purpose.

Client side: `resources/genro.js` 450 lines, `target.py` 61.

Tests: the machinery is covered today by `genro-builders`' own reactive
examples (`contrib/html/examples/reactive/09`–`19`, run by
`test_examples.py`) plus `test_data_presentation`. `genro-ws-web` has no
test suite. Any move of the code must decide where the coverage goes —
moving the code without the examples loses it.

---

## Riferimenti

Session-id: 6962ddd1-a3a9-4b94-8571-a279b59416a9.
