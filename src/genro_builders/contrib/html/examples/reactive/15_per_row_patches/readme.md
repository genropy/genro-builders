# 15 — Per-row patches

The iterate block stops re-rendering wholesale: each data event under
the anchor patches ONE row block.

## The classification

A data event whose reader is an iterate component classifies by path
arithmetic: the residual of the mutated path against the anchor names
the row (its first segment). The kind says what happened to it:

- a field changed, or the row replaced wholesale → `row_upd`;
- the row born (`ins` at depth one) → `row_ins`;
- the row dead (`del` at depth one) → `row_del`.

Everything else (the collection node itself replaced, non-iterate
readers) re-renders as before.

## The patch unit

The derived identity (`<base>.<label>.<ordinal>`) makes the row block
addressable: the body's first element is ordinal 1, so the block IS
`<base>.<label>.1` — pure arithmetic, nothing captured at event time:

- `row_upd` → `replace` of the block (`render_expansion_block`: same
  prep, same body, same registration as the walk — the ORACLE asserts
  the fragment appears verbatim in a full render);
- `row_ins` → `insert` anchored before the NEXT row's block in the
  collection's bag order (after the last row: the first renderable
  source sibling after the component);
- `row_del` → `remove` by derived id; the dead row's writeback
  entries are purged at patch time (its rules already died at the
  delete event, anchor-based).

## Cell patches: {id, value} downstream too

A mutation that touches ONE leaf of a row does not even re-render the
block: at registration the walk builds a per-COMPONENT catalog
(field -> ordinal: the body is code, the ordinal of "who shows
`.field`" is the same for every row) and the flush ships value-only
ops — `text` for a reader span, `attr` for a bound input — read from
the store, no body call, no re-registration. The broadcast case (the
exchange rate recomputing EVERY row) becomes exactly N tiny value
patches: cells never coalesce. Leaves the catalog does not know
(templates, checked, richer cells) fall back to the row replace.

## Density limits

`CELLS_PER_ROW_LIMIT` collapses a mostly-rewritten row into its own
replace; `ROW_COALESCE_LIMIT` collapses a STRUCTURAL flood of rows
into the enclosing container replace.

## Why it matters

Measured on the scale demos (container-replace era): one qty
edit cost ~60ms at 30 rows, ~600ms at 300, ~30s at 3000 (a quadratic
re-registration on top of the linear render). With per-row patches
the edit cost stops depending on the collection size.

Run it from this folder:

```bash
python per_row_patches.py
```
