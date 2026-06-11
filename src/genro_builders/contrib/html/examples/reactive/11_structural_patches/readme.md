# 11 — Structural patches

The source tree changes SHAPE at runtime: nodes attached and dropped
inside `live()` sections. Two new ops ride the same envelope as
`replace`:

```json
{"id": "n4", "op": "insert", "before": "n2", "html": "<li id=\"n7\">…</li>"}
{"id": "n3", "op": "remove"}
```

- **insert** — the new fragment only. `id` is the container's target_id
  (`null` = the document root), `before` the target_id of the following
  sibling (`null` = append). The siblings never travel — an `<iframe>`
  sitting next to the mutation would NOT reload.
- **remove** — the id is all the client needs. It is captured at the
  delete event, while the node is still in hand: by flush time the
  node is gone from the source.

## The target_id serial

Patch ids are **per-document serials** (`n1`, `n2`, …), assigned to
each node on first emission and stored on the object — the legacy
bridge (the id of the generating node), made deterministic. Being
bound to the object and not to its position, no structural mutation
can stale them: a positional or path-based id would shift with every
insert. The reactive render (`include_datapath`) emits the serial as
the DOM `id` of EVERY element: any element can become a patch target,
a container or an anchor at runtime — not predictable at first paint.

## What the artifacts show

`patches.json` logs four sections:

1. append (`todo.li("apples")`) → one insert, `before: null`;
2. positioned insert (`node_position="<"`) → the anchor is the target_id
   of the first item;
3. delete (`todo.value.pop("li_1")`) → one remove;
4. a node born and died in the SAME section → the optimizer nets
   ins+del to nothing: the batch is empty, the DOM never saw it.

The netting matrix lives in `_optimize_render`: `upd` after `ins` is
absorbed (the insert renders fresh), `del` after `ins` cancels both,
`ins` after `del` (same label re-created) becomes remove + insert at
the final position. Anchors skip transparent siblings (data-elements)
and pending ones (their own insert applies later in the batch); a
component sibling has no bounding element, so the insert falls back
to replacing the container.

## The safety net

The end-to-end oracle (`tests/test_partial_render.py`) applies every
batch to the previous full document with a reference element-tree
applier: the result must equal a fresh full render. Insert, remove
and their interleavings stay pinned to that equivalence.

Run it from this folder:

```bash
python structural_patches.py
```
