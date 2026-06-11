# 13 — Row logic

Per-row business logic declared in an iterated body — and WHEN it
runs.

## The rule is a rule of mutation

A real document loads COMPLETE: an invoice arrives with its totals
already right, and they are the truth of the document — recomputing
them at render would be redundant at best and wrong at worst (a
rounding rule changed since the invoice was issued would corrupt a
historical document). So:

- **the render never computes anything** — the expansion walk only
  CATALOGS the rules (`handler.expansion_logic`: resolved trigger
  path → rule node, per row, purged by row prefix at re-expansion);
- `_on_start` (and `data_setter`) inside an expansion body raise an
  explicit error: there is no "start" of a row, only its mutations.

## The trigger resolution

At registration each row's rule bindings resolve to absolute paths:

- `qty="^.qty"` → `rows.r3.qty` — different per row: the event fires
  ONE row;
- `rate="^header.rate"` → the SAME path for every row: one header
  event recomputes them all (the exchange-rate case);
- nested iterates scope for free: a group-level binding resolves
  inside its own group, so the event touches only that group's rows.

A row recomputes **iff the mutated path is among ITS resolved
bindings**. No special cases.

## The cascade

The rule executes in the data-event cascade (same queue, same
anti-loop): its write re-enters the event flow, so chained rules
(`qty → total → converted`) settle in one live section, and the
canonical readers (grand totals reading the store) follow.

Run it from this folder:

```bash
python row_logic.py
```
