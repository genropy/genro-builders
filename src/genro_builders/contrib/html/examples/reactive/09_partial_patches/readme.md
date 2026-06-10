# 09 — Partial patches

The render destination as an object: instead of a raw target (a path,
a writable, a callable) the page registers a **TargetWrapper**. The
render does not know who is behind it — the wrapper declares what it
consumes:

- `full(document)` — the total render (every wrapper supports it);
- `partial(patches)` — a batch of per-node patches, delivered by the
  `live()` flush when the wrapper declares `accepts_partial`.

## The patch envelope

```json
{"id": "body.div_0", "op": "replace",
 "html": "<div style=\"color: blue\" id=\"body.div_0\" ...>Martin</div>"}
```

- **id** — the node's structural path, the SAME string the reactive
  render emits as the DOM id under `include_datapath` (the wrapper
  asks for it via `render_opts`): the client finds the element by id
  and replaces it.
- **op: replace** — the re-rendered node, attributes included (outer
  fragment). One op covers text, attributes and structure — the
  Hotwire-style trade-off already in the contract. The envelope is
  open: finer ops (`set_attrs`, `set_text`) will ride it when
  per-attribute granularity lands.
- Patches arrive **in batches**, one per live section.

## What the artifacts show

`output.html` is the initial full render; `patches.json` logs every
batch. Note the second batch: two mutations on the SAME node produce
two identical patches — correct (the equivalence with the full render
holds, replace is idempotent) but wasteful. Removing that duplicate
is the optimizer's job (`_optimize_render`: exact dedup, then
ancestor-covers-descendant), the next step of this series.

## The safety net

The automated end-to-end oracle lives in
`tests/test_partial_render.py`: apply the patches to the previous
full document (a reference element-tree applier) and the result must
equal a fresh full render, canonicalized. Any future optimization
stays pinned to that equivalence.

Run it from this folder:

```bash
python partial_patches.py
```
