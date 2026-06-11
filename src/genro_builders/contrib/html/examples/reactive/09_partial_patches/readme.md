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
{"id": "n3", "op": "replace",
 "html": "<div style=\"color: blue\" id=\"n3\" ...>Martin</div>"}
```

- **id** — the node's `target_id` serial, the SAME string the reactive
  render emits as the DOM id under `include_datapath` (the wrapper
  asks for it via `render_opts`): the client finds the element by id
  and replaces it. The serial is assigned on first emission and bound
  to the OBJECT, not to its position — no structural mutation can
  stale it (see example 11).
- **op: replace** — the re-rendered node, attributes included (outer
  fragment). One op covers text, attributes and structure — the
  Hotwire-style trade-off already in the contract. The structural
  pair (`insert`, `remove`) is in example 11; finer ops (`set_attrs`,
  `set_text`) will ride the same envelope when per-attribute
  granularity lands.
- Patches arrive **in batches**, one per live section.

## What the artifacts show

`output.html` is the initial full render; `patches.json` logs every
batch — and each one shows an optimizer property (`_optimize_render`):

1. one mutation → ONE patch of the smallest unit (the `span`, not the
   page);
2. two mutations read by the SAME node → **exact dedup**, one patch
   carrying the last value;
3. ancestor (the card's style) and descendant (the name inside it)
   both touched → **ancestor covers descendant**, one patch of the
   card containing the fresh span.

Density coalescing (N siblings → one parent patch) is a policy with a
real trade-off (bytes and client state vs message count): deliberately
absent until measured on real scenarios.

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
