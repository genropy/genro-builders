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
| `archive/docs/contract.md` | `docs/builders/contract.md` | "builder name is prepended", "reactive_store" — replaced by `manager-architecture.md` |
| `archive/docs/architecture.md` | `docs/builders/architecture.md` | Describes the legacy BindingManager + store model |
| `archive/docs/reactive-data.md` | `docs/builders/reactive-data.md` | Uses `reactive_store.subscribe(...)` |
| `archive/docs/advanced.md` | `docs/builders/advanced.md` | Documents removed APIs `suspend_output()` / `resume_output()` |
| `archive/docs/creating-builder-packages.md` | `docs/builders/creating-builder-packages.md` | Uses `reactive_store` and `data_controller` |
| `archive/docs/svg-builder.md` | `docs/builders/svg-builder.md` | Uses removed property `builder.output` |

### tests/

| Archive path | Original path | Marker found |
|--------------|---------------|--------------|
| `archive/tests/test_main_store.py` | `tests/test_main_store.py` | `global_store` |
| `archive/tests/test_manager.py` | `tests/test_manager.py` | `global_store` + legacy register API |
| `archive/tests/test_manager_hooks.py` | `tests/test_manager_hooks.py` | `global_store` |
| `archive/tests/test_reactive_manager.py` | `tests/test_reactive_manager.py` | `global_store` + legacy register API |
| `archive/tests/test_async_build.py` | `tests/test_async_build.py` | `ComponentResolver` (removed) |
| `archive/tests/test_autonomous_builder.py` | `tests/test_autonomous_builder.py` | `.data["page.title"]` manual prepend |
| `archive/tests/test_abs_datapath.py` | `tests/test_abs_datapath.py` | Legacy grammar; to be rewritten against §6.1 |
| `archive/tests/test_binding.py` | `tests/test_binding.py` | Legacy pull-model reactive binding |
| `archive/tests/test_build_e2e.py` | `tests/test_build_e2e.py` | Mixed: legacy `page.lines.a.total` asserts + new failing test |
| `archive/tests/test_compiler_base.py` | `tests/test_compiler_base.py` | Suspect (deleted in wip by the user) |
| `archive/tests/test_data_builder.py` | `tests/test_data_builder.py` | Suspect (deleted in wip by the user) |
| `archive/tests/test_data_element.py` | `tests/test_data_element.py` | Exercises build/formula/cache on the legacy model |
| `archive/tests/test_dependency_graph.py` | `tests/test_dependency_graph.py` | Whole-file archive (integration half is legacy; unit half will be rebuilt) |
| `archive/tests/test_iterate.py` | `tests/test_iterate.py` | Suspect (deleted in wip by the user) |
| `archive/tests/test_node_id.py` | `tests/test_node_id.py` | Symbolic form to be rewritten against §6.5 |
| `archive/tests/test_pointer_formal.py` | `tests/test_pointer_formal.py` | Failing; assumes legacy grammar |
| `archive/tests/test_pointer.py` | `tests/test_pointer.py` | Legacy pointer parsing/resolution |
| `archive/tests/test_reactivity_edge_cases.py` | `tests/test_reactivity_edge_cases.py` | Legacy reactive model |
| `archive/tests/test_render_target.py` | `tests/test_render_target.py` | Failing auto-render edge cases |
| `archive/tests/test_runtime_attrs.py` | `tests/test_runtime_attrs.py` | Failing; evaluate_on_node legacy path |
| `archive/tests/test_live/` (6 files: `__init__.py`, `conftest.py`, `test_protocol.py`, `test_proxy.py`, `test_registry.py`, `test_server.py`) | `tests/test_live/` | `global_store`, `.data["page.xxx"]`, legacy `LiveServer`/`live_proxy` setup |

### examples/

| Archive path | Original path | Reason |
|--------------|---------------|--------|
| *(populated by archive commits 3.3)* | | |
