# 10 — Patch economics

A dashboard-shaped page — scattered fields, a computed total
(`data_formula` over the rows), a 40-row iterated table — instrumented
with a metrics wrapper. The committed `metrics.json` logs every batch
as patch ids and byte sizes: **these numbers are the basis of the
optimization decisions**, and the diff net keeps them honest.

## What the numbers say

| Scenario | Patches | The story |
|---|---|---|
| one scattered field | 1 × ~38 B | the minimal unit, nothing to improve |
| one field of ONE row (of 40) | total ~47 B + **table ~1960 B** | the whole-table patch costs ~40× the single row (~49 B): the **per-row refinement** (patch id = component path + item label) is worth it, and its value scales linearly with the collection size |
| a new row (atomic record) | total + table | structural change: the container patch is legitimate; a per-row `ins` op would still save most of it |
| three scattered mutations | 4 patches, the small ones stay small | no density coalescing needed: scattered patches are tens of bytes — the only heavy unit is the iterate container |

Two lessons beyond the numbers:

- the **formula cascade** rides the same flush: mutating a row patches
  both the table and the total — two readers, one section, one batch;
- a new row is **composed first and attached in ONE write**
  (`Bag({...})` then `set_item`): the cascade fires per logical
  mutation, and a strict formula must never see a half-written row.

## Decisions this example pins down

1. **Per-row refinement: justified.** Next step of the series — the
   expansion blocks get DOM ids (`component path + label`), the flush
   maps the mutated residual to the single block.
2. **Density coalescing: not now.** Scattered patches are cheap; the
   measured pain is elsewhere.

Run it from this folder:

```bash
python patch_economics.py
```
