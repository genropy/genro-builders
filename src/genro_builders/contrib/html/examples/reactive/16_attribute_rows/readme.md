# 16 — Attribute-mode rows

Legacy parity: the grid rides **values or attributes**. In attribute
mode a row is ONE bag node — the columns are its attributes, the node
value is free for the natural datum (a description).

## Why it matters at scale

- the store is FLAT: N nodes instead of N × columns;
- a whole row arrives as ONE `ins` event with its columns aboard;
- one `upd_attrs` event per attribute write, on the NODE path — the
  per-row classification (example 15) catches it with no special
  case: one row patch, the siblings never travel.

## The dialect

The bag speaks it natively, end to end:

- store: `set_item("rows.r1?qty", 2)` / `get_item("rows.r1?qty")`;
- pointers: `^.?qty` from the row anchor (`abs_datapath` keeps the
  `?attr` tail — it was in the contract from day one, DAT.2);
- write-back: the input's hook carries `main.rows.r1?qty`; the mutate
  lane resolves the node and writes the attribute;
- row logic: bindings on attributes register with the `?attr` tail
  and the matching strips it before the compare (same rule as the
  pointer_map): the `upd_attrs` event fires the row's rules, the
  destination `.?total` writes back an attribute.

Run it from this folder:

```bash
python attribute_rows.py
```
