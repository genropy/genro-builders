# 17 — Formula queue

Inside a live section a write no longer EXECUTES the dependent
formulas: it QUEUES them. The drain runs once, at the outermost exit,
before the render flush.

## The queue

- **FIFO with dedup on the pendings.** The key is `(spec, row)` for a
  component rule, the node for a page data-element — one queue for
  both. A key already pending does not queue twice: when it drains it
  reads the settled inputs anyway.
- **Re-queueing after execution is legitimate.** A formula that
  already drained can be woken again by a write that happened later
  in the drain — that is a new input, not a duplicate. The dedup is
  only on the pendings.
- **FIFO = layers.** On each event the component rules queue BEFORE
  the page readers, so the row-level writes land before the wide
  readers (a grand total) that depend on them.

## Controllers stay synchronous

A command is not a function of the state: two commands are two
executions, and the dedup would eat the second. The FIRE payload does
not persist — a deferred controller would read `None`. Controllers
(component rules and page data-elements alike) run at once.

## What it buys

A page-wide reader — the grand total, binding `^rows` — used to run
once per EVENT: a shared-binding broadcast over N rows meant N
executions, each O(N). Profiled at 1500 rows: ONE such formula took
the broadcast from 113ms to 2.9s. With the queue the N row rules
drain ahead of it while it stays pending, and it runs ONCE, on the
settled state.

On a chained edit (qty → total → converted → grand) the wide reader
runs twice: the user's own write wakes it once before the row chain
has run, the chain re-queues it once more. Bounded by the dependency
depth — never by the number of rows.

## The backstop

Two formulas feeding each other (`ping` reads `pong`, `pong` reads
`ping`, both always writing a new value) would make the drain spin
forever. A per-key counter (`FORMULA_REQUEUE_LIMIT`) stops it with an
explicit error naming the rule.

Run it from this folder:

```bash
python formula_queue.py
```
