# Archive — material incompatible with the current contract

**Source of truth**: `docs/builders/manager-architecture.md` (v0.2.0+,
🟡 APPROVATO CON RISERVA).

This directory holds tests, docs, and examples that contradict one or
more of the 13 invariants defined in the contract. They are **preserved,
not deleted**: every file can be recovered either by:

- reading it in place under `archive/<category>/<original-path>`;
- running `git log --follow archive/<category>/<file>` to see its full
  history, including the commits before the archive move;
- moving it back with `git mv` to its original path (the `--follow`
  tracker keeps working across moves).

## Layout

```
archive/
├── README.md                     ← you are here
├── docs/                         ← doc files that contradict the contract
├── tests/                        ← tests that assert on legacy data model
└── examples/
    ├── legacy-numbered/          ← old 01_..12_ examples (use reactive_store, data_controller, prepend)
    └── wip-renamed/              ← wip reorganisations (01-sync/, 02-async-live/) — same content, new paths
```

Every archived file keeps the **same relative path as its original**
under its category directory. Example: `tests/test_main_store.py` is
archived at `archive/tests/test_main_store.py`.

## Why archive rather than delete

- The contract is "approved with reservations": some invariants may
  still evolve. Recovering the original material is cheap insurance.
- Legacy tests often encode intent (what the system was supposed to do).
  Reading them side-by-side with the new suite accelerates review of
  coverage gaps.
- Legacy examples illustrate patterns that, once remapped to the new
  contract, could become the seeds of new examples.
- `git log --follow` remains useful for archaeology.

## What is **not** in archive

- `docs/builders/manager-architecture.md` — the contract itself. It
  lives under its canonical path.
- Tests that survived the triage (schema, autocomplete, compile parent,
  component proxy / slots, yaml renderer, `test_builders/`, `builders/`).
- Docs that are neutral (quickstart, faq, html-builder, markdown-*,
  validation, xsd-builder, custom-builders, custom-renderers, examples)
  or navigation hubs (`README.md`, `index.md`) that are updated in place
  to drop the archived cross-references.
- `contrib/jupyter/` — new, alignment with contract to be verified in a
  follow-up phase but not archived by default.

## Invariants violated per category

For a full, numbered list of the 13 invariants, see §13 of
`docs/builders/manager-architecture.md`. Short summary of the violations
that drive the archive decisions here:

| Invariant | Expected behaviour | Typical legacy violation |
|-----------|---------------------|--------------------------|
| #1 Local isolation | A builder reads/writes only its own local_store (or via explicit volume) | `app.global_store["page.x"]` |
| #2 No prepend | `abs_datapath` never inserts the builder name | `page.` auto-prefix |
| #3 No silent fallback | Unresolvable path → `ValueError` | silent empty read |
| #7 Pull-based formulas | `data_formula` on demand | push-based `data_controller` |
| #8 Volume only cross-builder | No back channel to other builders' data | `self._manager.get_item(other_path)` |
| #10 Manager is registry | No monolithic data bag | `self._data = Bag()` at manager root |
| #12 Single data access channel | Reads via `get_relative_data` / writes via `set_relative_data` | `data.get_item(...)` / `data.set_item(...)` |

## Index

This file is the static entry point. A detailed index of every archived
file (→ original path, invariant violated, §) is maintained below and
kept in sync after each archive commit.

### docs/

| Archive path | Original path | Reason |
|--------------|---------------|--------|
| *(populated by archive commits 3.1)* | | |

### tests/

| Archive path | Original path | Marker found |
|--------------|---------------|--------------|
| *(populated by archive commits 3.2)* | | |

### examples/

| Archive path | Original path | Reason |
|--------------|---------------|--------|
| *(populated by archive commits 3.3)* | | |
