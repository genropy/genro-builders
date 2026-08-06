# Superseded design documents

Design records whose subject **no longer exists in the code and is not
carried forward by the contract in force**. They are kept, not deleted:
a design document explains why a mechanism was shaped the way it was,
and that reasoning outlives the mechanism.

Three folders, three different criteria — do not mix them:

| Folder | Holds |
|---|---|
| `roadmap/outdated_versions/` | superseded **versions of the contract** itself (`architecture-contract-v0.3.md` … `-v0.8.0.md`, plus the renderer addendum). The delta between versions is in `roadmap/CONTRACT_CHANGELOG.md`. |
| `roadmap/superseded/` | **design documents** for machinery that was removed and is not being redesigned. |
| `roadmap/reactivity/` | the reactive design, **still pending**: superseded as written (against contract v0.5.0) but explicitly carried forward by `RX.4`/`RX.5` as the starting material of the separate reactive engine. Not superseded — unbuilt. |

Where the removed code itself can be fished out of git is recorded in
`roadmap/reactivity/removed-machinery.md`: a commit sha is exact
forever, a copy in an `attic/` rots in silence.

## Contents

- `application-model.md` (moved 2026-08-04) — the `live()` critical
  section as the context of reactivity, and the Application↔`BuilderHandler`
  dual relationship. Both subjects are gone: `live()` and the patch
  protocol left with the reactive apparatus in 0.20.0, `BuilderHandler`
  itself was removed in `a83e61e` (the datastore belongs to the
  builder), and the application layer is no longer an area of this
  contract — it lives in genro-ws-web (`APP` retired, contract v0.9.0).
