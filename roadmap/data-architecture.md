# Data architecture

**Version**: 0.1.0
**Last Updated**: 2026-05-12
**Status**: 🔴 DA REVISIONARE — Documento non ancora approvato.
**Audience**: Contributors writing or maintaining `genro-builders`,
and users building applications on top of `BuilderHandler`.

This document is the companion of
[architecture-contract.md](architecture-contract.md). The contract
fixes the twelve high-level decisions on builder, handler, render
and compile; this document describes the **data model** that lives
on the handler: storage, path grammar, pointers, datapath, volumes,
data access API, errors.

The first commit is a **table of contents + minimal scoping**
(1–3 paragraphs per section). Each section will be expanded in
follow-up commits, one at a time.

---

## Table of contents

1. [Scope and placement](#1-scope-and-placement)
2. [Conceptual model](#2-conceptual-model)
3. [Path grammar](#3-path-grammar)
4. [`datapath` as a node attribute](#4-datapath-as-a-node-attribute)
5. [`^pointer` as a value](#5-pointer-as-a-value)
6. [`abs_datapath` — the single resolver](#6-abs_datapath--the-single-resolver)
7. [Application API — `get_relative_data` / `set_relative_data`](#7-application-api--get_relative_data--set_relative_data)
8. [Volumes and cross-handler access](#8-volumes-and-cross-handler-access)
9. [DataBuilder — shared data pattern](#9-databuilder--shared-data-pattern)
10. [Symbolic pointers and `node_by_id`](#10-symbolic-pointers-and-node_by_id)
11. [Expected errors](#11-expected-errors)
12. [Invariants of the data model](#12-invariants-of-the-data-model)
13. [What is not in this document](#13-what-is-not-in-this-document)
14. [Glossary](#14-glossary)

---

## 1. Scope and placement

This document covers the **data layer** of `genro-builders`: where
data lives, how it is named, how nodes in the source and built tree
reference it, and which API is allowed to read or write it. It is
a companion to [architecture-contract.md](architecture-contract.md);
that contract is the source of truth for handler/builder/render
separation, this document is the source of truth for everything
data-related.

The scope is the **complete model**: five canonical pointer forms,
the same five forms for `datapath`, the `?attr` suffix, the
volume mechanism for cross-handler access, and the `DataBuilder`
pattern for shared data. Reactivity is mentioned only as a
forward reference (§13.1): the model defined here makes reactivity
possible, but the dispatch mechanism is the subject of a
separate document.

The previous data architecture is preserved as historical
reference in
[../archive/docs/builders/manager-architecture.md](../archive/docs/builders/manager-architecture.md)
(v0.2.0, blueprint). That version was builder-centric (the data
lived on the builder). The current model is **handler-centric**:
the handler owns the data. The reasoning is given in §2.

---

## 2. Conceptual model

A `BuilderHandler` represents a **document** (for example: a
customer invoice). A document has three parallel facets that the
handler owns together:

- **Schema / grammar** — provided by the builder
  (`handler.builder`), which is grammar-only since the
  renegotiation of decision 8 (2026-05-12).
- **Data** — the live values of the document, owned by the handler
  as `handler.data` (a `Bag`).
- **Presentation** — produced by `handler.renderer` reading
  `handler.built` + `handler.data`.

Because the data is part of the document's identity (loading an
invoice means populating `handler.data`), the data lives on the
handler, not on the builder. Sub-builders (decision 2:
`@subbuilder(SvgBuilder)`) **share** the handler's data; they do
not own a local store of their own.

The handler's lifecycle is unchanged from
[architecture-contract.md §5](architecture-contract.md):
`create` populates `source`, `build` materializes `built`,
`render` serializes `built`. Data writes can happen at any
moment after `__init__` and before — or in between — render
calls. The renderer reads `handler.data` on every render, so
re-rendering with new data produces new output without rebuilding.

---

## 3. Path grammar

A **path** identifies a location inside a data store. The same
grammar is used for two purposes: the body of a `^pointer` (a value
that references data) and the value of the `datapath` attribute (a
context shifter on a node). Five canonical forms exist:

| Form | Example | Meaning |
|------|---------|---------|
| Absolute | `customer.name` | Path inside the current handler's `data`. |
| Relative | `.name` | Concatenated with the closest absolute ancestor anchor. |
| Volume | `cfg:theme.primary` | Path inside the volume registered as `cfg` on the handler. |
| Symbolic | `#billing.lines` | Resolve `node_id="billing"` on the source side, take its `datapath`, append the tail. |
| Volume + symbolic | `cfg:#root.locale` | Symbolic lookup inside a named volume. |

A path may carry an optional `?attr` suffix:
`customer.name?color` reads the `color` attribute of the data node
at `customer.name`. The suffix is orthogonal to the five forms.

The grammar is intentionally identical for pointers and
`datapath`. This means anything the user can write after `^` they
can also write as a `datapath` value (without the leading `^`),
and the resolution rules are the same. Symbolic forms (`#id`) are
**source-time only**: the built tree does not keep a `node_id`
index, so `#id` paths must be resolved before reaching the built.

---

## 4. `datapath` as a node attribute

`datapath` is an attribute on a node that shifts the **data
context** for that node and every descendant. When a child node
contains a relative pointer (`^.x`), resolution walks up the
ancestor chain and combines `datapath` values until it finds an
absolute anchor.

Combination rules:

- A **relative** `datapath` (`.x`) **concatenates** onto the
  parent's effective datapath.
- An **absolute** `datapath` (plain, volume, symbolic, or
  volume + symbolic) **resets** the chain — anything above it is
  discarded.
- A volume on an ancestor (`cfg:customer`) **propagates** to
  descendants: a `.lines` below it yields `cfg:customer.lines`,
  still inside the `cfg` volume.

The walk stops at the first absolute anchor. If no absolute anchor
is found, a relative pointer below cannot resolve — the system
raises a `ValueError` (§11). There is no silent fallback to "root
of the data store".

---

## 5. `^pointer` as a value

A `^pointer` is a string that starts with `^` and carries the
intent "read the data at this path". It can appear as a node's
value or as a node's attribute. In the **source** tree, pointers
are written verbatim by the user. In the **built** tree, pointers
**remain strings** — they are not resolved during build.

Pointer resolution happens just-in-time at render or compile time,
on the node. The renderer or compiler reads `node.runtime_value`
or `node.runtime_attrs`, which trigger the resolution chain. This
late-binding makes it possible to render the same `built` multiple
times with different data, producing different outputs — the
property reactivity is built on.

Pointer values are never mutated in place: a write to the data
store updates the value at the path, not the pointer string on
the node. The pointer is the *reference*, not the value.

---

## 6. `abs_datapath` — the single resolver

`abs_datapath(path)` is the **only** primitive that converts a
path (in any of the five forms) into an absolute, fully-qualified
string. It lives on the node (both source-side and built-side),
walks the ancestor chain when needed, applies volume routing, and
delegates symbolic lookup to `node_by_id` (§10).

The rules are absolute:

- **No prepend** — the handler name (or any other prefix) is never
  silently inserted.
- **No fallback** — an unresolvable path raises an exception.
  Missing volume → `KeyError`. Relative without anchor →
  `ValueError`.
- **No drift between source and built** — both sides honour the
  same grammar. The only difference is that the source side can
  resolve symbolic forms (`#id`) because it keeps a `node_id`
  index; the built side raises on symbolic input.

`abs_datapath` is a **low-level primitive**. Application code
(data elements, renderers, compilers, reactive callbacks) **must
not** call it directly. The single application entry point is the
pair described in §7. `abs_datapath` is exposed only for
infrastructure that needs a path string without a read (typically
dependency-graph registration).

---

## 7. Application API — `get_relative_data` / `set_relative_data`

Every application read or write on the data store goes through two
methods on the node:

```python
node.get_relative_data(path)          # read
node.set_relative_data(path, value)   # write
```

Both accept the full path grammar of §3 (absolute, relative,
volume, symbolic, volume + symbolic, plus `?attr`). Internally
they call `abs_datapath` to resolve, route the operation to the
correct store (`handler.data` for absolute/relative, the volume's
data for `vol:...`), and on writes set an anti-loop marker so the
mutating node does not re-fire its own subscribers.

A scalar companion exists for the common case "this value may or
may not be a pointer":

```python
node.current_from_datasource(value)
# if is_pointer(value): return self.get_relative_data(value[1:])
# else:                 return value
```

This helper composes on top of `get_relative_data`; it does not
duplicate any resolution logic.

**Forbidden in application code**: calling `handler.data.get_item`
/ `set_item` directly, calling `abs_datapath` followed by a
hand-rolled read/write, or reaching into `handler.data` by any
other path. There is one channel; if a use case does not fit, the
channel is extended — not bypassed.

---

## 8. Volumes and cross-handler access

A **volume** is a named reference to another data store, exposed
to a handler through a registry. The only way for handler `A` to
read or write data owned by handler `B` is to register `B` as a
volume on `A` and reference it via `^volname:path`.

The registry is owned by the handler:

```python
handler.register_volume("cfg", other_handler)
# ...then pointers like  ^cfg:theme.primary
# resolve to              other_handler.data["theme.primary"]
```

Cross-handler resolution flows entirely through `abs_datapath` →
the registry → the target handler's `data`. There is no shortcut,
no manager back-channel, and no implicit "current handler context"
exposed to user code. If the registry does not know the volume
name, the read fails with a `KeyError`.

Volumes are the **only** legitimate cross-handler vehicle.
Anything else (a function that takes both handlers and reads from
the second one, a global module-level reference, a shared
singleton) is a layering violation.

---

## 9. DataBuilder — shared data pattern

A `DataBuilder` is a handler dedicated to **data ownership**: it
has a schema (declared via `@component` and `field`) but no
renderer and no compiler. It exists to hold data that is read by
multiple presentation handlers — invoices, PDFs, dashboards — via
volume references.

The typical setup is one or more `DataBuilder`s registered as
volumes on the presentation handlers:

```python
data_h = InvoiceData()        # DataBuilder: customer, lines, totals
page   = InvoicePage()        # HtmlBuilderHandler
pdf    = InvoicePdf()         # PdfBuilderHandler

page.register_volume("data", data_h)
pdf.register_volume("data",  data_h)

# Both handlers read ^data:customer.name, ^data:lines.total, etc.
```

`DataBuilder` is the way to give data **an identity**: a name, a
schema, a place. Domain data goes into a `DataBuilder`;
presentation-local state can stay on the presentation handler.
When two or more handlers read the same value, a `DataBuilder`
is the correct home for that value.

---

## 10. Symbolic pointers and `node_by_id`

A symbolic pointer (`^#node_id.field`) names a source node by its
declared `node_id` rather than by a path. Resolution looks up the
node in the handler's `node_by_id` index, takes its `datapath`,
and appends the tail.

The `node_by_id` design is already fixed (memory:
`project_node_by_id_design`). Stage 1 dispatch covers two special
scopes:

- `^#FORM.x` — nearest ancestor with `is_form=True`.
- `^#ANCHOR.x` — nearest ancestor with `is_anchor=True`.

Any other `node_id` resolves nominally: the handler scans the
source for a node whose `node_id` attribute matches. Collisions
raise an error at registration time. Symbolic resolution is
source-side only; the built tree raises if a symbolic form
reaches it (because the built has no `node_id` index — it is a
purely executional tree).

---

## 11. Expected errors

The data layer fails loudly. The expected exceptions are:

| Exception | Where | Meaning |
|-----------|-------|---------|
| `ValueError: Unresolved relative datapath` | `abs_datapath` (built side) | A `^.x` has no absolute ancestor anchor. |
| `ValueError: Relative datapath without anchor` | `abs_datapath` (source side) | Same condition during `main()`. |
| `KeyError: Volume '<name>' not registered` | volume routing | A `^vol:x` referenced an unknown volume. |
| `KeyError: No node with node_id '<id>'` | `node_by_id` | A `^#id.x` named an unknown node. |
| `ValueError: Symbolic path on built side` | `abs_datapath` (built) | A `^#id.x` reached the built tree. |

No silent default. No empty string. No `None` masquerading as a
miss. Each error names what is missing and where.

---

## 12. Invariants of the data model

The contractual properties the data layer always upholds:

1. **Handler ownership** — `handler.data` is private to the
   handler. Only volumes expose it to other handlers.
2. **No prepend** — no code injects a handler name into a path.
3. **No silent fallback** — unresolvable paths raise.
4. **Built is formal** — `^pointer` strings live verbatim in the
   built; resolution is render/compile-time only.
5. **Resolution on the node** — only `BuiltBagNode` resolves
   `^pointer`. Renderers and compilers read `runtime_value` /
   `runtime_attrs`; they do not interpret `^...` themselves.
6. **One read/write channel** —
   `node.get_relative_data` / `node.set_relative_data` are the
   only application entry points.
7. **One resolver** — `abs_datapath` is the only primitive.
   Source side and built side share the contract.
8. **Volume is the only cross-handler vehicle** — no back-channel.
9. **Single-root component** — a component produces exactly one
   top-level node (from
   [architecture-contract.md §7](architecture-contract.md#7-source-preserva-la-ricetta-dellutente-component-lazy)).

These invariants are enforced by the implementation (raises) and
by code review (the channel rule).

---

## 13. What is not in this document

The following topics are referenced here for completeness but
covered elsewhere or postponed:

- **13.1 Reactivity** — change propagation from `handler.data` to
  renderer/compiler. Forward reference: blueprint
  [../archive/docs/builders/manager-architecture.md §11](../archive/docs/builders/manager-architecture.md).
- **13.2 Domain-data vs UI-state separation** — whether to split
  the data store into a domain part and a UI part. Deferred
  2026-04-28. Five options (α–ε) explored, none adopted.
  See memory `project_path_separation_deferred`.
- **13.3 Special scopes `WORKSPACE` / `ROW` / `DATA`** — additional
  symbolic scopes beyond `FORM` / `ANCHOR`. Postponed to Stage 2+;
  will be added when concrete use cases emerge.

Each topic above is a candidate for its own companion document.

---

## 14. Glossary

| Term | Meaning |
|------|---------|
| **handler** | A `BuilderHandler` instance — a document. Owns `source`, `built`, `data`, `renderer`, `compiler`, `render_target`. |
| **data** | `handler.data`: the `Bag` that holds the live values of the document. |
| **builder** | The grammar-only object (`handler.builder`). Defines tags, validation, build rules. |
| **source** | The user's recipe, populated in `create`. |
| **built** | The materialized tree, produced in `build`. Holds `^pointer` strings verbatim. |
| **path** | A string identifying a location in a data store, in one of five canonical forms. |
| **pointer** | A `^path` string that references data. Resolved at render/compile time. |
| **datapath** | A node attribute that shifts the data context for descendants. Same grammar as the body of a pointer. |
| **anchor** | The closest absolute `datapath` found while walking ancestors. Required to resolve a relative pointer. |
| **volume** | A named reference to another handler's `data`, exposed via the handler's volume registry. |
| **DataBuilder** | A handler dedicated to data ownership — schema + data, no renderer, no compiler. |
| **node_id** | A source-side identifier used by symbolic pointers `^#id.x`. |
| **`abs_datapath`** | The low-level primitive that converts any path form into an absolute string. Single resolver. |
| **`get_relative_data` / `set_relative_data`** | The two application-level read/write entry points on a node. |

---

**End of document. Sections will be expanded in follow-up
commits, one at a time, as decided in the originating session
plan (2026-05-12).**
