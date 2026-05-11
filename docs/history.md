# Project history — genro-builders

This document reconstructs how the project arrived at its current
shape, and records the operating convention for local worktrees. It
complements `architecture-contract.md` (the *what* of the architecture)
by explaining the *why* — what was tried before, what was kept, what
was dropped.

## Timeline

### 22 March 2026 — Initial structure

Commit `7470ee8` bootstraps the project skeleton.

### 22 April 2026 — Manager-architecture contract introduced

Commit `3c66159` adds `docs/builders/manager-architecture.md` as the
target-architecture contract (v0.2.0, *approvato con riserva*). The
document fixes 13 invariants for manager, builder, pointer and volume
semantics:

- Local-store-per-builder model (no `global_store`).
- `DataBuilder` + `volume` as the only cross-builder data channel.
- Pointer/datapath grammar parity (plain, relative, volume, symbolic,
  volume + symbolic).
- `abs_datapath` as the single low-level resolver; `_resolve_datapath`
  absorbed.
- `{get,set}_relative_data` as the only applicative data-access
  channel; `current_from_datasource` as scalar helper on top.

The commit also declares the policy that drives the next four days:
**the rest of the repository is brought into alignment with this
document, not the other way around.**

### 23 April 2026 — `archive/` plan executed

Four commits move every file that contradicts the v0.2.0 contract
into a new `archive/` tree on the working branch:

- `91a25ff` bootstraps `archive/` layout + `archive/README.md`.
- `469d0f9` moves 6 contract-incompatible docs into `archive/docs/`.
- `0038478` moves contract-incompatible tests into `archive/tests/`.
- `7a15b30` moves 12 legacy numbered HTML examples into
  `archive/examples/legacy-numbered/`.

After this step the working branch is no longer a snapshot of the
prototype — it is a hybrid of "new code aligned with v0.2.0" and
"preserved-but-deprecated material under `archive/`".

### 24–29 April 2026 — Work under v0.2.0

About twenty commits land on the working branch implementing the
v0.2.0 plan:

- 24 April — eradicate `builder_name` prepend from `abs_datapath`;
  fix `_pipeline_builder` on built shell.
- 26 April — refactor `Manager` into a pure registry,
  `builder.data` autonomous; single-channel data access via
  `{get,set}_relative_data` with volume routing; reactive manager
  with per-builder subscribe and coalescing; rename
  `_resolve_datapath` to `_walk_ancestor_datapath`; test coverage of
  the five canonical pointer forms.
- 27 April — coverage of `data_setter`, `data_formula`, cascading,
  computed attributes.
- 28 April — no silent strip-`.` in `_walk_ancestor_datapath`
  (no-fallback policy enforced).
- 29 April — component `main_*` / `main_kwargs` at call time;
  iterate `TypeError` on `@element` and non-Bag target; preserve
  `node_id` on built nodes.

### 1 May 2026 — From-scratch rebuild begins

Two commits change strategy: instead of continuing to patch the
v0.2.0 plan, the build pipeline is rewritten from zero.

- `62e382a` introduces `_BuildMixinNew` for HTML build rebuild from
  scratch.
- `b19780e` mirrors plain HTML source into the built tree.

This is the start of what the May handoff called the *restart*. The
working branch that contains these commits is later frozen as the
`archive/2026-04-blueprint` reference.

### 3 May 2026 — `decisions.md` drafted

A new design document is drafted at
`temp/2026-05-03/decisions.md`. It captures twelve decisions on
builder/handler separation, layering, lifecycle phases, render
contract, source preservation under `@component`. The file is in
`temp/` (gitignored) — it is a workspace document, not yet a contract.

### 10 May 2026 — `architecture-contract.md` promoted

Commit `f017277` introduces `docs/architecture-contract.md` as the
*source of truth*, promoted from `temp/2026-05-03/decisions.md`. The
same commit lands `BuilderHandler`, the two-level bag layering, the
generic build mirror and the XML default render.

From this point onward:

- `archive/2026-04-blueprint` is frozen — *read-only reference,
  never amended*.
- `develop` evolves under `architecture-contract.md`.
- Renegotiations of any decision are recorded **in the contract
  file itself**, with a dated note, not on side documents.

### 11 May 2026 — Reorganisation: `genro-builders-restart/` retired

For ten days `develop` was checked out in a side-by-side worktree
named `genro-builders-restart/`. On 11 May the situation was cleaned
up:

- `genro-builders-restart/` removed; `genro-builders/` (the primary
  worktree, already registered in Claude Code's session store) now
  holds `develop`.
- `genro-builders/worktrees/` introduced as a gitignored container
  for local-only secondary worktrees.

The term *restart* is retired in favour of *develop* / *blueprint*.

## Worktree convention

The repository is consumed locally through two roles:

### Primary worktree

`sub-projects/genro-builders/` is the single primary worktree. It is
always checked out on `develop` and is where all work happens. The
package is `pip install -e .` from here.

### Consultation worktree (`worktrees/readonly/`)

`sub-projects/genro-builders/worktrees/readonly/` is a gitignored
secondary worktree used only to look at the codebase at any past
commit or branch — typically the blueprint, but in principle any
arbitrary ref. The cartella is treated as **read-only by
convention**: never commit, never edit from there.

When the consultation target changes, the worktree is removed and
recreated:

```bash
git worktree remove worktrees/readonly
git worktree add --detach worktrees/readonly <commit-or-branch>
```

`--detach` is intentional: the worktree is parked on a commit, not
on a branch label, so there is no risk of accidentally advancing a
branch from there.

### Parallel work worktrees

If parallel work on a separate branch is needed (long-running
feature, hotfix isolated from develop, etc.), create a dedicated
worktree with a *specific name* under `worktrees/`:

```bash
git worktree add worktrees/<feature-name> <branch>
```

These worktrees are also gitignored, but they are *not* read-only —
they are working copies. Naming them descriptively keeps them
distinct from the `readonly/` consultation slot.

### Why this layout

- One primary tree → no ambiguity about where `develop` lives, no
  duplication of install state.
- Gitignored `worktrees/` container → secondary checkouts never
  pollute the branch, never get pushed by accident.
- Consultation under a fixed `readonly/` slot → unique entry point
  for looking at history; the *content* of the slot rotates while
  the path stays the same.
- Parallel workspaces under named slots → cohabit with the
  consultation slot without colliding.

## See also

- `docs/architecture-contract.md` — the source of truth for the
  twelve decisions (with dated renegotiation notes).
- Branch `archive/2026-04-blueprint` (HEAD `14d1ebd`) — the frozen
  reference of the pre-restart prototype. The `archive/` directory
  inside that branch is itself a historical artefact: it was the
  v0.2.0 plan to keep contract-incompatible material *next to*
  the new code in the same tree.
