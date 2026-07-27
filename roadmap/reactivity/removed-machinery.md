# Removed machinery — where to look when reactivity is redesigned

**Status**: 🟢 riferimento operativo (non un design).
**Last Updated**: 2026-07-27

Two removals took the reactive apparatus out of the core, in this order.
Nothing was copied into an `attic/`: a **commit sha is exact forever**,
while a copy rots in silence and nobody notices. This file is the map of
where to look.

## 1. The engine (2026-07-26, `2f48b4a`)

`src/genro_builders/builder/data_handler.py`, 1148 lines:

    git show 2f48b4a^:src/genro_builders/builder/data_handler.py

Held the rule engine (`RuleSpec`, `ComponentRules`, `RowContext`), the
`live()` critical section and the `@live` decorator, the formula queue,
the render queue (`add_render_path`, `render_nodes`), the lazy lane, the
patch economics (`_optimize_render`, `RenderEntry`, `record_removed_id`).

**Worth taking back**: `live()` is not reactive machinery, it is a
**batch** — take the lock, accumulate, drain the formula queue at the
outermost exit, then apply. The formula queue itself (dedup on the
pendings, FIFO as layering, `FORMULA_REQUEUE_LIMIT` turning an `a -> b ->
a` livelock into an error that NAMES the rule) is domain logic,
independent of the target.

**Not worth taking back**: the rule engine existed because the rows did
not — you could not attach a formula to a row, so you attached a template
to an anchor and dispatched it by coordinates. If a row becomes a node,
the template becomes a node and there is nothing left to coordinate.
Same for `_expansion_row`, which DEDUCED which row changed by path
arithmetic: with a real node the label is read, not deduced.

**The measured defect not to repeat**: `_relevant_nodes` scanned the
WHOLE map on every mutation with a `startswith` per key — 36M
`startswith` on a 3000-row broadcast (`28e210e`). Cause: a flat map of
strings, so "who is under this path" is a linear scan. With a hierarchy
it is a descent.

## 2. The tracking (2026-07-27, this commit; parent `52b2b73`)

    git show 52b2b73:src/genro_builders/builder/builder_handler.py
    git diff 52b2b73 -- src/genro_builders/builder/base.py
    git diff 52b2b73 -- src/genro_builders/builder/source_bag.py

What left:

| What | Where it was |
|---|---|
| `BuilderHandler` (whole file, 129 lines) | `builder/builder_handler.py` |
| `add_builder` — mounted the builder and ran `create()` | same file |
| `pointer_map` + `_register_path` / `_unregister_pointer` / `_update_pointer_map` | same file |
| `application` — the Application hook | same file, `__init__` |
| source subscribe armed in `create()` | `builder/base.py` |
| `_on_source_event`, `_on_upd_value`, `_on_upd_attrs`, `_value_nature`, `on_source_change` | `builder/base.py` |
| `_is_reactive` property | `builder/base.py` |
| `node.handler` and `node.data_handler` properties, `_handler` slot | `builder/source_bag.py` |

**Why, and it is a deliberate exception.** The project rule is not to
delete predisposed scaffolding without verifying its intent. Here the
intent is *not verifiable*: the reactive engine is at its third or fourth
attempt with no outcome, so keeping its infrastructure means paying an
advance that is never collected — and constraining the next design to a
shape drawn for the previous attempts. Better a minimal static core; the
reactive engine will bring its own structure, designed for itself.

## What replaced them, and reads better

- **`builder.data`** is THE datastore, one flat Bag owned by the builder.
  There is no second object to build and bind.
- **`node.data`** reaches it from any node through the ancestor walk —
  same name at every level, so nobody wonders which object to go through.
  It works on a detached tree (a component expansion) too, which the old
  `node.handler` could not: that returned `None` there, and
  `data_handler` needed two attempts to work around it.
- **`get_subbuilder`** passes the DATASTORE down to a sub-builder, where
  it used to pass the handler. Same invariant, the right object.
- **`target_id`** tells a document node from an expansion node by asking
  whether the tree's root is the builder's own `_sourceroot` — no slot,
  no handler.

Measured: `base.py` + `source_bag.py` + the handler went from 1891 lines
to 1627 (**-264**) and one file. The render output did not change by a
byte — `test_examples.py` compares the committed output.

## What did NOT leave, and why

`get_relative_data` / `set_relative_data` and the `SET`/`GET`/`PUT`/`FIRE`
macros stay, `fired` and `reason` included. They are not reactive
scaffolding: the flags travel through `genro_bag`'s subscribe pipeline,
which carries them, and **nothing in this package acts on them**. They
are the vocabulary a data-element func uses on its node.
