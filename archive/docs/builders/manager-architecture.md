# Manager, Builders, Pointers, Volumes — Target Architecture

**Version**: 0.2.0
**Last Updated**: 2026-04-22
**Status**: 🟡 APPROVATO CON RISERVA — this is now the source of truth for the manager + builder + pointer + volume architecture. Subsequent code, tests, and examples are brought into alignment with this document, not the other way around. Reservations are itemised in §14 (migration to-do) and will be lifted as each item is addressed.
**Maintained By**: Genropy Team
**Audience**: Contributors writing or maintaining `genro-builders`, and
users building on top of `BuilderManager` / `ReactiveManager`.
**Prerequisites**: Familiarity with `genro-bag` (`Bag`, `BagNode`,
`set_backref`, subscribers, resolvers) and with the `^pointer` concept.

---

## Reading Guide

This document describes the **target architecture** for the data layer of
`genro-builders`: the decisions frozen on 2026-04-22 after the "no-prepend,
no-fallback" turn.

- Sections 1–4 set the scene: what a builder, a manager, a renderer and
  a data store are in this codebase.
- Sections 5–7 define the **pointer grammar** and the **volume model** —
  the contract every builder must honour.
- Sections 8–10 cover the two "sides" of the data infrastructure:
  `DataBuilder` (schema for shared data) and the two built-in data
  elements (`data_setter`, `data_formula`).
- Section 11 is the deep dive on **reactivity**.
- Section 12 revisits render and compile, with an eye on pointer
  resolution.
- Section 13 lists the **invariants** the system is required to uphold.
- Section 14 enumerates what has to die in the current tree for this
  target to be reached. Appendices finalise the picture with a file
  map, flow diagrams and a quick reference card.

The target architecture treats the data namespace as a **federation of
private Bags coordinated by name** (volumes). There is no shared data
Bag. There is no automatic path rewriting. If a path does not resolve,
the system fails loudly.

---

## 1. Foundations

### 1.1 The four actors

| Actor | Responsibility |
|-------|----------------|
| **Builder** (`BagBuilderBase`) | Owns a grammar, a `source` Bag, a `built` Bag, a `local_store` (data) Bag. Materializes source into built. |
| **Manager** (`BuilderManager` / `ReactiveManager`) | Registers N builders by name. Orchestrates `setup → build → render`. Resolves volumes. Hosts the reactive dispatch. |
| **Renderer** (`BagRendererBase`) | Transforms the built Bag into serialized output (string/bytes). |
| **Compiler** (`BagCompilerBase`) | Transforms the built Bag into live objects (widgets, workbooks, DOM). |

### 1.2 The three Bags per builder

Every builder owns three `Bag` instances, each with a well-defined role:

| Bag | Role |
|-----|------|
| `source` | The recipe. Populated once by `main()` with grammar-driven calls. |
| `built` | The materialized structure. Produced by `build()`. Contains components expanded and elements materialized. `^pointer` strings stay verbatim — they are **not** resolved at build time. |
| `local_store` (= `data`) | The data store for this builder. Lives and dies with the builder, owned privately. Read by `^pointer` during render/compile. |

### 1.3 Cardinal principle

> **No automatism. No fallback. No silent prepend.**

The system resolves only what the user wrote. Missing pieces raise
`ValueError` with a message that points at the missing piece. The builder
name is **never** inserted into a path. Cross-builder access exists, but
it is always explicit (volume syntax).

### 1.4 Global topology

```{mermaid}
flowchart TB
    subgraph Manager["BuilderManager / ReactiveManager"]
        REG["volumes registry<br/>{name: local_store}"]
        DG["DependencyGraph (reactive)"]
        RT["RenderTargets (reactive)"]
    end

    subgraph BA["Builder 'page' (HtmlBuilder)"]
        SA[source_A]
        BU_A[built_A]
        LS_A[local_store_A]
        R_A["renderers / compilers"]
    end

    subgraph BB["Builder 'store' (DataBuilder)"]
        SB[source_B]
        BU_B[built_B]
        LS_B[local_store_B]
    end

    Manager --- BA
    Manager --- BB
    REG -.-> LS_A
    REG -.-> LS_B
```

The manager does not own a monolithic data Bag. It owns a **registry of
references** to each builder's `local_store`. Volume resolution (`^store:x`)
is a lookup in this registry.

---

## 2. The Builder as a Machine

### 2.1 Internal composition

`BagBuilderBase` is composed from four mixins plus an encapsulated
reactivity engine:

| Module | Class / Mixin | Responsibility |
|--------|---------------|----------------|
| [src/genro_builders/builder/_grammar.py](../../src/genro_builders/builder/_grammar.py) | `_GrammarMixin` | Element dispatch, validation, schema access |
| [src/genro_builders/builder/_component.py](../../src/genro_builders/builder/_component.py) | `_ComponentMixin` | Component proxy creation, slots |
| [src/genro_builders/builder/_build.py](../../src/genro_builders/builder/_build.py) | `_BuildMixin` | Build walk, materialization, dependency registration |
| [src/genro_builders/builder/_output.py](../../src/genro_builders/builder/_output.py) | `_OutputMixin` | `render`, `compile`, `check`, `validate` |
| [src/genro_builders/builder/_reactivity.py](../../src/genro_builders/builder/_reactivity.py) | `ReactivityEngine` | Subscribe, incremental compile (per-builder) |
| [src/genro_builders/builder/base.py](../../src/genro_builders/builder/base.py) | `BagBuilderBase` | Init, schema boot, pipeline properties |

The three compile-time mixins share `self`. `ReactivityEngine` is a
separate object (`self._reactivity`) created lazily on the first
`subscribe()` call. A builder that never subscribes never pays the
reactivity cost.

### 2.2 Pipeline properties

```python
builder.source    # BuilderBag — user populates it via grammar calls
builder.built     # BuiltBag   — produced by build()
builder.data      # Bag        — the local_store (alias for legacy readers)
```

`builder.data` is the **builder's own local_store**. When the builder is
registered in a manager, the manager keeps a reference to the same Bag
under the builder's name in the volumes registry. There is no separate
"managed data" — the local_store is always owned by the builder.

### 2.3 Lifecycle of a single builder

```
grammar boot         __init_subclass__ scans decorators → _class_schema
instantiate          __init__: shells, source/built/local_store
populate             main(source) or setup() at manager level
build                _build_walk (2 phases: walk + finalize)
(optional) subscribe ReactivityEngine activates bindings
render / compile     output via registered renderer/compiler
```

### 2.4 What a builder does NOT do

- A builder **does not** prepend its own name to any path.
- A builder **does not** read another builder's data directly.
  Cross-builder access goes through the manager volume registry.
- A builder **does not** perform side effects. Side effects belong to
  `data.subscribe()` callbacks on the data store.
- A builder **does not** auto-render on data changes. The manager
  (when configured) dispatches output.

---

## 3. The Manager

### 3.1 Role: registry and coordinator

The manager is **not a data store**. It is a registry of builders indexed
by name, plus orchestration for the lifecycle. The target API is:

| Method | Purpose |
|--------|---------|
| `on_init()` | Subclass hook: register builders here. |
| `register_builder(name, cls, **kw)` | Instantiate and register a builder under a name. |
| `local_store(name=None)` | Return the local_store Bag of a builder (by name, or current). |
| `resolve_volume(name)` | Semantic alias used during pointer resolution: `^name:path` → this Bag. |
| `main(source)` / `main_<name>(source)` | Populate source (dispatch). |
| `setup()` | Run main dispatch for every registered builder. |
| `build()` | Materialize every registered builder. |
| `run()` | `setup()` then `build()`. |

`BuilderManager` keeps the lifecycle synchronous; `ReactiveManager`
extends it with `subscribe()` and a cross-builder `DependencyGraph`
(see Section 11).

### 3.2 `on_init()`

The manager exposes `on_init()` as the subclass hook for registering
builders. It is called exactly once, at the end of `__init__`.

```python
class InventoryApp(BuilderManager):
    def on_init(self):
        self.data = self.register_builder("data", InventoryData)
        self.page = self.register_builder("page", InventoryPage)
```

Each call to `register_builder` does three things:

1. Instantiates the builder and wires its `_manager` back-reference.
2. Records the builder in the internal `{name: builder}` map.
3. Records a reference to the builder's `local_store` under the same
   name in the volume registry.

There is **no** manager-side `set_item("<name>", Bag())`. The local_store
belongs to the builder; the manager only indexes it.

### 3.3 `main()` dispatch

```python
class InventoryApp(BuilderManager):
    def on_init(self):
        self.data = self.register_builder("data", InventoryData)
        self.page = self.register_builder("page", InventoryPage)

    def main_data(self, source):
        source.customer().field("name").field("vat")

    def main_page(self, source):
        source.body().h1("^data:customer.name")
```

`setup()` iterates the registered builders in insertion order. For each
one it looks for `main_<name>` on the manager and calls it with the
builder's `source`. If no `main_<name>` is defined and there is **only
one** builder, `main(source)` is used instead.

During the dispatch the manager sets an internal pointer
(`_current_builder_name`) so that `self.local_store()` with no argument
resolves to the bag of the builder currently being populated.

### 3.4 End-to-end: multi-builder with DataBuilder

```python
from genro_builders.manager import BuilderManager
from genro_builders.contrib.html import HtmlBuilder
from genro_builders.contrib.data import DataBuilder
from genro_builders.builder._decorators import component


class InventoryData(DataBuilder):
    @component()
    def customer(self, comp, **kw):
        comp.field("name", dtype="text", name_long="Customer name")
        comp.field("vat",  dtype="text", name_long="VAT number")

    def on_configure(self):
        self.source.customer()


class InventoryApp(BuilderManager):
    def on_init(self):
        self.data = self.register_builder("data", InventoryData)
        self.page = self.register_builder("page", HtmlBuilder)

    def main_page(self, source):
        source.body().h1("^data:customer.name")


app = InventoryApp()
app.data.data["customer.name"] = "Acme S.r.l."
app.data.data["customer.vat"]  = "IT12345678901"
app.run()
print(app.page.render())
```

Observations:

- The manager owns nothing that looks like "global_store". The `data`
  builder's local_store plays that role, but only by convention.
- The HTML page reads `^data:customer.name`, where `data` is the volume
  name (the builder name registered in the manager).
- `InventoryData.on_configure()` declares the schema once at
  registration time.

### 3.5 `run()` and async

`run()` is `setup()` followed by `build()`. `build()` returns `None` in
synchronous contexts and a coroutine when any registered builder's build
is asynchronous (the `smartcontinuation` infrastructure absorbs the
branching). Callers use `smartawait` to be indifferent:

```python
from genro_toolbox import smartawait

# Sync:
app.run()

# Async:
await smartawait(app.run())
```

---

## 4. The Data Model

### 4.1 One local_store per builder

Every builder owns an independent `Bag` as its local_store. Ownership is
strict: the builder writes it, reads it, and hands a reference to the
manager only for volume lookup.

There is **no** global_store. There is **no** shared reactive_store.
There is **no** sub-partitioning by name inside some other Bag.

### 4.2 Shared data = `DataBuilder` + volume

When two or more builders need to read the same data, the solution is
always the same: register a `DataBuilder` dedicated to that data, and
have the other builders reference it by volume (`^name:path`).

Rationale:

- The data has an identity (it is the `data` builder's responsibility)
  rather than being "floating" across presentation builders.
- The data has a schema, via `field` / `@component`.
- Cross-builder access is explicit in every `^pointer`, which makes
  dependencies searchable.

### 4.3 Responsibility table

| Operation | Writes where | Reads where |
|-----------|--------------|-------------|
| `data_setter("x")` inside builder `page` | `page.local_store["x"]` | — |
| `data_setter("config:theme")` inside `page` | `config.local_store["theme"]` (volume) | — |
| `p(value="^title")` inside `page` | — | `page.local_store["title"]` |
| `p(value="^data:customer.name")` inside `page` | — | `data.local_store["customer.name"]` |
| `data_formula(".total", ...)` inside `page` | `page.local_store[<resolved from datapath>]` | Pointers in kwargs resolve via the built context. |

### 4.4 Data-flow diagram

```{mermaid}
flowchart LR
    subgraph Pgr["page (HtmlBuilder)"]
        PLS[(local_store<br/>page)]
    end
    subgraph Dta["data (DataBuilder)"]
        DLS[(local_store<br/>data)]
    end
    subgraph Cfg["config (DataBuilder)"]
        CLS[(local_store<br/>config)]
    end

    PLS -- "write '.total'" --> PLS
    PLS -- "read '^title'" --> PLS
    PLS -- "read '^data:customer.name'" --> DLS
    PLS -- "read '^config:theme.bg'" --> CLS
```

---

## 5. Pointer Syntax (formal grammar)

### 5.1 What a pointer is

A `^pointer` is a string, starting with `^`, that carries the intent
"read from the data store at this path". The built Bag holds these
strings verbatim; they are resolved **just-in-time** during render or
compile.

Grammar (informal):

```
pointer      := "^" [ volume ":" ] path [ "?" attr ]
volume       := IDENT                    (builder name registered in manager)
path         := absolute | relative | symbolic
absolute     := IDENT ( "." IDENT )*     (e.g. "customer.name")
relative     := "." IDENT ( "." IDENT )*  (e.g. ".price")
symbolic     := "#" IDENT ( "." IDENT )* (e.g. "#address.street")
attr         := IDENT                    (attribute of the data node)
```

### 5.2 The four canonical forms

| Syntax | Resolves to |
|--------|-------------|
| `^field` | The path `field` **inside the current builder's local_store**. No prepend is applied. |
| `^.field` | Relative: the closest ancestor `datapath` is combined with `field`. Resolution stays inside the current local_store. |
| `^volume:field` | Absolute path `field` inside the local_store of the builder registered as `volume`. |
| `^#node_id.field` | Symbolic: find the source node whose `node_id` attribute equals `node_id`, take its `datapath`, append `.field`. Symbolic form is build-time only (see §6.5). |
| `^volume:#node_id.field` | Symbolic with volume: look up `node_id` in the `volume` builder's source, use its `datapath`, append `.field`. Also build-time only. |

The `?attr` suffix is orthogonal: `^path?color` reads the attribute
`color` of the data node at `path`.

### 5.3 Parser

Parsing is centralized in
[src/genro_builders/builder/_binding.py](../../src/genro_builders/builder/_binding.py)
as `parse_pointer(raw) -> PointerInfo`:

```python
PointerInfo(
    raw: str,
    path: str,
    attr: str | None,
    is_relative: bool,
    volume: str | None,
)
```

`is_pointer(value)` checks the `^` prefix; `scan_for_pointers(node)`
walks a node's value and attributes to collect every pointer.

### 5.4 Absolute rules

1. A **relative pointer never leaves** the current builder's local_store.
   If the ancestor chain does not provide an absolute anchor, resolution
   raises `ValueError`.
2. An **absolute pointer without `:`** is never prefixed with a builder
   name. The user's string is the store path, verbatim.
3. A **pointer with `:`** is routed through the manager's volume registry.
   If the registry does not know `volume`, resolution raises `KeyError`.
4. `^pointer` strings **remain strings** in the built Bag; resolution is
   strictly on-demand.

### 5.5 Examples of well-formed and ill-formed pointers

```python
"^title"            # OK: reads <current builder>.local_store["title"]
"^.name"            # OK if an ancestor provides datapath="users.0" → "users.0.name"
"^data:customer"    # OK: reads data.local_store["customer"]
"^.name"            # ValueError if no ancestor has a datapath
"^missing:x"        # KeyError: volume 'missing' not registered
```

A `volume:` prefix combined with a `.relative` tail is parsed but the
result is undefined by the current architecture — treat the combination
as non-portable and avoid it. The canonical way to read a relative slice
of another builder's store is to first write an anchor there and read it
absolutely.

---

## 6. Datapath and Anchor Resolution

### 6.1 The `datapath` attribute

`datapath` is a node attribute that sets the **data context** for that
node and all its descendants. Its grammar is the **same** grammar as
the body of a `^pointer` (just without the leading `^`): a datapath is
a path, and every path shape the system understands in pointers is
also understood in `datapath`.

The canonical forms:

| Form | Example | Meaning |
|------|---------|---------|
| Absolute (local) | `datapath="users.0"` | Set the data context to `users.0` in the current local_store. Resets the chain. |
| Relative | `datapath=".address"` | Concatenated with the parent's effective datapath. |
| Volume | `datapath="data:customer"` | Set the data context to `customer` inside the `data` volume. Resets the chain and changes the store. |
| Symbolic | `datapath="#billing.lines"` | Resolve `node_id="billing"` in the current builder's source, take its datapath, append `.lines`. Resets the chain. |
| Volume + symbolic | `datapath="data:#billing.lines"` | Resolve `node_id="billing"` in the `data` builder's source, apply the tail. |

Walking up the ancestor chain and combining these values yields an
**effective datapath** for every node. Relative pointers (`^.x`) resolve
by concatenating this effective datapath with the tail `x`.

The rules that govern combination across the chain:

- A **relative** ancestor (`.xxx`) is concatenated onto the current
  effective datapath.
- An **absolute** ancestor (any of the non-relative forms: plain,
  volume, symbolic, volume + symbolic) **resets** the chain — everything
  above it is discarded.
- A volume that appears in a datapath propagates to descendants: if
  `datapath="data:customer"` sits at one level and a descendant has
  `datapath=".lines"`, the effective datapath is `data:customer.lines`,
  still pointing into the `data` volume.

### 6.2 One primitive: `abs_datapath`

Resolution is a **single** primitive method: `node.abs_datapath(path)`.
Given any path in the pointer grammar (§5), it returns the absolute
path in the appropriate local_store — walking the ancestor chain when
needed, applying volume routing, keeping the behaviour consistent
across source and built sides.

```python
def abs_datapath(self, path: str) -> str:
    """
    Resolve any path form to an absolute datapath.

    Rules (target):
      1. "volume:path" → return "volume:path" unchanged (routing is
         performed at read/write time via the manager registry).
      2. "./relative"  → walk ancestor datapaths; if no absolute anchor
                         is found, raise ValueError. If an ancestor
                         carries a volume (e.g. 'data:customer'), that
                         volume propagates to the resolved path.
      3. "#node_id…"   → resolve symbolically by looking up node_id
                         (source side only; on the built side this
                         raises because the id map does not exist).
      4. "absolute"    → return "absolute" unchanged.
    """
```

The method **never** prepends a builder name. It performs no silent
substitution. A relative path without an anchor is an error, not a
fallback.

There is no separate "`_resolve_datapath`" primitive in the target
architecture. The ancestor walk over `datapath` attributes is **part
of** `abs_datapath` — an internal step, not a public contract. The
dualism that exists today in the tree (a public-ish `_resolve_datapath`
being called around `abs_datapath`) is a leftover to be collapsed: see
migration item #13.

Source:
[src/genro_builders/built_bag.py](../../src/genro_builders/built_bag.py)
(built side) and
[src/genro_builders/builder_bag.py](../../src/genro_builders/builder_bag.py)
(source side). The same contract, the same rules. The source-side
version is the only one that can resolve the symbolic form, because
the built tree has no node_id index.

> **`abs_datapath` is a low-level primitive.** Application code — data
> elements, renderers, compilers, reactive callbacks — must not call
> it. The single applicative entry points are
> `node.get_relative_data(path)` / `node.set_relative_data(path, value)`
> (§10.6), which use `abs_datapath` internally. `abs_datapath` remains
> exposed only for infrastructure that needs a path-string without a
> read, most notably dependency graph registration.

### 6.3 Ancestor walk (internal step of `abs_datapath`)

When `abs_datapath` receives a relative path, it walks up the ancestor
chain collecting `datapath` attributes. Relative values (`.xxx`)
concatenate; absolute values in any of the §6.1 shapes (plain, volume,
symbolic, volume + symbolic) reset the chain. This is a step of the
resolution, not a separate public method.

```{mermaid}
flowchart TB
    A["div node<br/>no datapath"] --> B["section node<br/>datapath='.address'"]
    B --> C["article node<br/>datapath='users.0'"]
    C --> D["root"]
    A -. "resolves via ancestors" .-> E["effective: 'users.0.address'"]
```

If `A` contains `p(value="^.street")`, the resolver produces
`users.0.address.street` and reads that path from the current local_store.

### 6.4 Resolution table

For every canonical pointer form, the outcome (relative to "current
builder `page` with ancestor chain providing `users.0.address`"):

| Raw pointer | `abs_datapath(...)` | Read from |
|-------------|---------------------|-----------|
| `^title` | `"title"` | `page.local_store["title"]` |
| `^.street` | `"users.0.address.street"` | `page.local_store["users.0.address.street"]` |
| `^data:company` | `"data:company"` | `data.local_store["company"]` |
| `^data:.company` | malformed | — |

### 6.5 Symbolic form (build-time only)

On the **source** side, `BuilderBagNode.abs_datapath` handles the
symbolic form by looking up a node by `node_id` and using its `datapath`
as the anchor. This is useful in `data_setter` / `data_formula` paths
written during `main()` before the built tree exists.

The symbolic form accepts a **volume prefix**: `^volume:#node_id.field`.
In this case `_resolve_symbolic` asks the manager for the builder
registered as `volume`, then looks up `node_id` in *that* builder's
source-side node-id map. The trailing `.field` is appended to the
symbol's `datapath`. This is the only cross-builder flavour of the
symbolic form; `#id` without a volume always resolves inside the
current builder.

Symbolic paths do not appear in built nodes' pointers, because the built
Bag is purely executional and does not keep a node-id index.

---

## 7. Volumes — Cross-Builder Access

### 7.1 The only cross-builder vehicle

`volume:path` in a pointer is the **only** way for one builder to read
data owned by another builder. There are no shortcuts: no
`manager.local_store(other)["x"]` injection into the builder's logic,
no back-channel, no "current manager context".

The manager holds the registry `{name: local_store}`. When
`abs_datapath` sees `volume:path`, the actual read is dispatched through
this registry by the render/compile pipeline (the pointer carries the
volume in its `PointerInfo.volume` field).

### 7.2 Canonical use cases

1. **Shared configuration** — A `config` DataBuilder holds theme,
   localization, feature flags. Every presentation builder reads
   `^config:theme.primary`, `^config:locale`, etc.
2. **Single-source-of-truth domain data** — An `orders` DataBuilder
   with the live order list. The checkout page, the invoice page, the
   dashboard all read `^orders:...`.
3. **Cross-widget reads** — In a multi-panel UI, the main content reads
   `^sidebar:selection` to stay in sync with the sidebar's choice.

### 7.3 What volumes are **not** for

Volumes are not a general escape hatch for "I need a convenient place
to stash some shared dict". If you find yourself spraying writes across
presentation builders through volumes, stop and introduce a `DataBuilder`.

Rules of thumb:

- Domain data → **always** in a `DataBuilder`.
- Presentation state (an input focus, a hover flag) → can live in the
  presentation builder's local_store.
- Anything read by two or more builders → DataBuilder + volume.

### 7.4 End-to-end: three builders with cross volumes

```python
from genro_builders.manager import BuilderManager
from genro_builders.contrib.html import HtmlBuilder
from genro_builders.contrib.data import DataBuilder
from genro_builders.builder._decorators import component


class Config(DataBuilder):
    def on_configure(self):
        self.source.field("theme.primary", dtype="text", default="#3355ff")
        self.source.field("locale",        dtype="text", default="it_IT")


class CartData(DataBuilder):
    @component()
    def cart(self, comp, **kw):
        comp.field("items", dtype="bag")
        comp.field("total", dtype="number")

    def on_configure(self):
        self.source.cart()


class Checkout(HtmlBuilder): ...


class Shop(BuilderManager):
    def on_init(self):
        self.config = self.register_builder("config", Config)
        self.cart   = self.register_builder("cart",   CartData)
        self.page   = self.register_builder("page",   Checkout)

    def main_page(self, source):
        source.body(style="color: ^config:theme.primary").h1("^cart:total")
```

Observations:

- Every cross-reference is explicit: `^config:theme.primary`,
  `^cart:total`.
- Presentation logic (`page`) never touches the shared data bags
  directly — it only references them via pointers.
- Adding a new presenter (e.g. a PDF receipt builder) is a one-liner in
  `on_init`; the new builder reads the same volumes.

### 7.5 Volume graph (diagram)

```{mermaid}
flowchart LR
    page -->|"^config:theme.primary"| config
    page -->|"^cart:total"| cart
    pdf  -->|"^cart:*"| cart
    pdf  -->|"^config:locale"| config
```

---

## 8. DataBuilder — Shared Data Pattern

### 8.1 What it is

`DataBuilder` ([src/genro_builders/contrib/data/data_builder.py](../../src/genro_builders/contrib/data/data_builder.py))
is a `BagBuilderBase` subclass with:

- **No renderers, no compilers** — it does not produce output.
- A minimal grammar centred on the `field` element:
  ```python
  field(dtype, name_long, name_short, format, default)
  ```
- The usual `@component` machinery, so related fields can be grouped
  and reused.

### 8.2 `on_configure()`

`BagBuilderBase.on_configure()` is a hook invoked at the end of
`__init__` (standard instantiation). DataBuilder subclasses override it
to populate the schema at registration time:

```python
class InvoiceData(DataBuilder):
    @component()
    def customer(self, comp, **kw):
        comp.field("name", dtype="text", name_long="Name")
        comp.field("vat",  dtype="text", name_long="VAT")

    @component()
    def lines(self, comp, **kw):
        comp.field("items", dtype="bag")
        comp.field("total", dtype="number", format="#,##0.00")

    def on_configure(self):
        self.source.customer()
        self.source.lines()
```

### 8.3 Pattern: single shared DataBuilder

```python
class App(BuilderManager):
    def on_init(self):
        self.data = self.register_builder("data", InvoiceData)
        self.page = self.register_builder("page", InvoicePage)
        self.pdf  = self.register_builder("pdf",  InvoicePdf)
```

Both `page` and `pdf` read `^data:customer.name` and
`^data:lines.total`. The data has one home and two presenters.

### 8.4 Pattern: multiple thematic DataBuilders

For apps with heterogeneous shared data:

```python
class App(BuilderManager):
    def on_init(self):
        self.config    = self.register_builder("config",   ConfigData)
        self.session   = self.register_builder("session",  SessionData)
        self.customers = self.register_builder("customers", CustomerData)
        self.page      = self.register_builder("page",     PagePresenter)
```

The presenter references volumes selectively:
`^config:locale`, `^session:user`, `^customers:<selected_id>.name`.

### 8.5 `HtmlManager` — the batteries-included pair

[src/genro_builders/contrib/html/__init__.py](../../src/genro_builders/contrib/html/__init__.py)
provides `HtmlManager`, a ready-to-use `ReactiveManager` that registers
an HTML page under the name `page` and a DataBuilder under the name
`data`. For single-page apps this is the standard starting point:

```python
from genro_builders.contrib.html import HtmlManager

class Hello(HtmlManager):
    def main(self, source):
        source.body().h1("^data:title")

app = Hello()
app.data.data["title"] = "Hello, world"
app.run()
print(app.page.render())
```

Note that `main(source)` is dispatched to the primary builder (`page`),
while `main_data(source)` (if defined) populates the DataBuilder's source.

---

## 9. Build Pipeline

### 9.1 Two phases

`build()` runs a two-phase walk:

- **Phase 1 — Walk**: traverse the source Bag, materialize normal
  elements into the built Bag, expand components (macro-like). Data
  elements (`data_setter`, `data_formula`) encountered during the walk
  are **accumulated**, not processed, so that when their paths are
  resolved the built ancestor chain is already complete.
- **Phase 2 — Finalize**: process accumulated data elements using the
  complete built tree for ancestor resolution; warm up formulas with
  `_on_built=True`; fire `_onBuilt` hooks; register render-time
  dependency edges in the manager's dependency graph.

Source:
[src/genro_builders/builder/_build.py](../../src/genro_builders/builder/_build.py)
— see `build()`, `_build_walk`, `_process_pending_data_elements`,
`_execute_data_setter`, `_install_formula_resolver`.

### 9.2 Components as transparent macros

A component source node does **not** produce a wrapper node in the
built. When expanded, its contents are spliced directly into the parent
target. This has two consequences:

- Calling the same component N times within a parent does not produce
  collisions: each materialised element's label is auto-generated by
  `grammar._child`.
- The component is a macro over the grammar, not a new level of nesting.

### 9.3 Single-root invariant and `main_tag`

`_expand_component` enforces that a component handler produces **exactly
one top-level node** (a tree, not a forest). If the schema declares
`main_tag="div"`, the top-level node's `node_tag` must match `div`.
Violations raise `ValueError` at build time.

### 9.4 `iterate` — replication over data children

```python
@component(sub_tags="")
def line_row(self, comp, **kw):
    comp.tr()\
        .td("^.product")\
        .td("^.qty")\
        .td("^.price")

source.line_row(iterate="^cart:lines.items")
```

For each child node under `cart:lines.items`, the build walk expands
`line_row` once and injects `main_datapath=".{child.label}"` into the
handler via framework-only `main_kwargs`. The handler splats
`main_kwargs` onto the main widget, so every replica has its own
absolute-on-entry datapath. Relative pointers like `^.product` then
resolve to `cart:lines.items.<label>.product`.

### 9.5 Build diagram

```{mermaid}
flowchart TB
    S["source Bag"] --> W["Phase 1: walk"]
    W -->|"elements"| B["built Bag"]
    W -->|"components"| E["expand (macro)"]
    E --> B
    W -->|"data_setter / data_formula"| P["_pending_data_elements"]
    B --> F["Phase 2: finalize"]
    P --> F
    F -->|"resolve abs_datapath via built"| LS[("local_store")]
    F -->|"install resolvers"| LS
    F -->|"register render/build edges"| DG[("DependencyGraph")]
```

---

## 10. Data Elements

### 10.1 The two built-ins

`BagBuilderBase` registers two data elements via `@data_element`:

```python
@data_element()
def data_setter(self, path, value=None, **kwargs):
    return path, dict(value=value, **kwargs)

@data_element()
def data_formula(self, path, func, **kwargs):
    return path, dict(func=func, **kwargs)
```

Both are **transparent**: they are recorded on the source side but do
not appear as nodes in the built Bag. They are consumed by Phase 2 of
the build walk.

### 10.2 `data_setter` — static write

During Phase 2, for each pending `data_setter`:

1. Resolve `path` via the built parent's `abs_datapath(path)`. No
   prepend, no fallback.
2. Resolve `value` through `current_from_datasource` (so that a `^x` in
   `value` reads from data immediately — rare, but supported).
3. If `value` is a `dict`, wrap it in a `Bag`.
4. Write to `data.set_item(resolved_path, value)`.

Example:

```python
def main(self, source):
    source.data_setter("title", value="Hello")
    source.data_setter(".fallback", value="n/a")   # inside a datapath block
    source.data_setter("data:company", value="Acme")  # writes to volume
```

### 10.3 `data_formula` — install a resolver

For each pending `data_formula`:

1. Resolve `path` via `abs_datapath` (same rules).
2. Build a `FormulaResolver` with the `func` and the remaining kwargs
   (pointer kwargs stay as `^...` strings — they are not resolved at
   install time).
3. Attach the resolver to the built parent as `_built_context` and the
   local_store as `_data_bag`.
4. Call `data.set_resolver(path, resolver)`.
5. Register formula dependency edges in the manager's graph.

Dependency pointers in the kwargs are resolved lazily by the resolver's
`on_loading(kw)` hook, which calls `built_context.abs_datapath(...)` at
load time. This is the feature that closes the loop on "no prepend":
since both install-time and load-time resolution go through the same
`abs_datapath`, the resolved paths are consistent.

See [src/genro_builders/formula_resolver.py](../../src/genro_builders/formula_resolver.py).

### 10.4 Formula cascades — pull chain

```python
source.data_setter("base", value=10)
source.data_formula("doubled",   func=lambda base:    base * 2,   base="^base")
source.data_formula("quadrupled", func=lambda doubled: doubled * 2, doubled="^doubled")
```

Reading `data["quadrupled"]` triggers its resolver, which reads
`data["doubled"]`, which triggers its own resolver, which reads
`data["base"]`. No topological sort is needed — the `Bag` / resolver
infrastructure gives it for free.

### 10.5 `_on_built`, `_onBuilt`, `_cache_time`, `_interval`

| Kwarg | Meaning |
|-------|---------|
| `_on_built=True` | Warm up the formula at the end of build (force one read). |
| `_onBuilt=callable` | Call `callable(builder)` exactly once at end of build. |
| `_cache_time=N` | N > 0: passive cache with TTL of N seconds. N == 0 (default): recompute on every read. |
| `_interval=N` | N > 0: active cache with a background refresh every N seconds. Stores result in the data node — triggers subscribers. Requires an async loop. |

Side effects (logging, HTTP, persistence) **do not** belong to
`data_formula`. They belong to `data.subscribe()` callbacks on the
local_store, typically wired by the manager.

### 10.6 Data access API — always go through the node

The two primitives on `BuiltBagNode` are the **only** supported way to
read from or write to the data store during build, render, compile,
formula execution and reactive dispatch:

```python
node.get_relative_data(path)          # read
node.set_relative_data(path, value)   # write
```

Both accept the full pointer grammar documented in §5 (absolute,
relative `.foo`, volume `x:foo`, symbolic `#id.foo`, volume + symbolic
`x:#id.foo`, plus `?attr_name` for attribute access). Internally they:

1. Call `self.abs_datapath(path)` to resolve.
2. Route the read/write through the appropriate local_store (current
   builder, or the volume the path points at).
3. On writes, set `_reason=self` automatically so the change does not
   re-fire the same node's own subscribers (anti-loop).
4. Raise `ValueError` / `KeyError` on any unresolved path — no silent
   fallback.

**Why one channel, not two.** If some code path used `abs_datapath` +
`data.get_item` by hand and another used `get_relative_data`, the two
would drift: one would pick up a new resolution rule, the other would
not. The volume registry, the anti-loop `_reason`, the `?attr` handling,
the error mode — they all live in this pair. One entry point means one
source of truth.

**The rule.** Every place in the codebase that needs to touch the data
store — data elements, formula resolvers, iterate expansion, render and
compile handlers, reactive callbacks, test helpers — reads via
`get_relative_data` and writes via `set_relative_data`. Two kinds of
direct call are considered a bug:

- `self.data.get_item(path)` / `self.data.set_item(path, value)` —
  bypasses the whole API, skips volume routing and anti-loop.
- `node.abs_datapath(path)` followed by a hand-rolled read or write —
  duplicates exactly what the relative API does internally, with the
  usual drift risk. `abs_datapath` is a low-level primitive (§6.2); it
  is not an application entry point.

**The one legitimate exception** is the underlying `Bag` plumbing that
`get_relative_data` and `set_relative_data` delegate to — i.e. the two
lines inside those two methods themselves. That is the bottom of the
stack; nothing above it bypasses it.

**What `abs_datapath` may still be called for.** Pure path-string
computation where no read is intended, most notably registering edges
in the `DependencyGraph` (§11.4). Those call sites need a textual path,
not a value; going through the relative API there would force a read
that does not belong in that control flow.

Example — a renderer that needs to peek at a sibling:

```python
@renderer()
def order_total(self, node, parent):
    qty   = node.get_relative_data(".qty")
    price = node.get_relative_data(".price")
    return f"<span>{qty * price}</span>"
```

Example — a reactive callback inside a compiler that wants to push a
computed value back:

```python
@compiler()
def slider(self, node, parent):
    widget = make_slider()
    widget.on_change(
        lambda v: node.set_relative_data(".value", v),
    )
    return widget
```

In both cases the resolution rules, volume support and anti-loop are
free.

### 10.7 `current_from_datasource` — scalar dereferencing helper

`current_from_datasource(value)` is a companion helper, not an
alternative channel. It operates on a **single value** rather than on a
path:

```python
def current_from_datasource(self, value):
    if is_pointer(value):
        return self.get_relative_data(value[1:])
    return value
```

Semantics: "given a value, if it is a `^pointer`, dereference it using
the relative API from this node's perspective; otherwise return the
value unchanged." It is the go-to helper in contexts where a field may
**or may not** hold a pointer — `evaluate_on_node`, attribute
resolution, callable defaults, and anywhere legacy code used to mix
literal values with pointer strings.

The key point: `current_from_datasource` **composes on top of**
`get_relative_data`, it does not duplicate its logic. The relative API
remains the single read/write primitive; this helper is one layer
above it, specialised to "resolve a scalar that may be a pointer".

Source of truth — [src/genro_builders/built_bag.py:189-193](../../src/genro_builders/built_bag.py#L189-L193):

```python
def current_from_datasource(self, value: Any) -> Any:
    """Resolve a single value: if ^pointer, read from data; else return as-is."""
    if is_pointer(value):
        return self.get_relative_data(value[1:])
    return value
```

The version that still lives on `BuilderBagNode`
([src/genro_builders/builder_bag.py:247-264](../../src/genro_builders/builder_bag.py#L247-L264))
predates the relative API and reimplements resolution by hand
(`abs_datapath` + `data.get_item`). That version must be realigned to
delegate to `get_relative_data` (see migration item §14.12).

**Rule for contributors.** Any new code that needs "resolve this value
if it happens to be a pointer" uses `current_from_datasource`. No new
code reintroduces the `abs_datapath` + `get_item` pair by hand.

---

## 11. Reactivity — `ReactiveManager` in depth

### 11.1 Two flavours of manager

`BuilderManager` is a one-shot orchestrator: `run()` returns, and the
app is responsible for calling `render()` / `compile()` when it wants
output.

`ReactiveManager` ([src/genro_builders/manager.py](../../src/genro_builders/manager.py))
extends it with:

- A `DependencyGraph` that tracks formula / render / build edges.
- A `subscribe()` method that hooks the manager into every local_store
  change via `set_backref` + `data.subscribe()`.
- Render targets (`set_render_target`) and automatic rendering.
- Event-loop-aware flushing.

### 11.2 Subscribing — what happens

`subscribe()` walks the registry and, for each builder, ensures
`local_store.set_backref()` is set, then attaches a single subscriber
(`self._SUBSCRIBER_ID = "reactive_manager"`) with `any=<callback>`. Every
change in any local_store routes back to the manager.

Additionally, every builder is asked to `subscribe()` on its own, so
that its `ReactivityEngine` can maintain per-builder incremental-compile
wiring if enabled.

### 11.3 Collect → flush → dispatch

The callback chain is intentionally split to coalesce bursts:

1. `_on_store_changed(...)` reconstructs the changed absolute path from
   `pathlist` + `evt`, appends it to `_pending_changes`, and schedules
   `_flush()` via `loop.call_soon(...)`. If no loop is running, it flushes
   synchronously.
2. `_flush()` drains `_pending_changes` and asks the `DependencyGraph`
   for `impacted_builders(changes)`. It then calls `on_data_changed(impacted)`.
3. `on_data_changed(impacted)`:
   - For each builder with `dep_type == "build"`: rebuild it.
   - For each registered render target for that builder: render and
     write, respecting `min_interval` throttling.

This three-step chain decouples "something happened" from "do work
now", so many tiny changes become one render.

### 11.4 `DependencyGraph`

[src/genro_builders/dependency_graph.py](../../src/genro_builders/dependency_graph.py)
holds an inverse index `{source_path: [DepEdge]}`. A `DepEdge` carries:

```python
@dataclass(frozen=True)
class DepEdge:
    source_path: str
    target: str
    dep_type: str          # 'formula' | 'render' | 'build'
    builder_name: str | None
```

Edges are registered during `build()`:

- `_register_formula_deps(formula_path, dep_paths)` — one edge per
  dependency pointer of a `data_formula`.
- `_register_dep(iterate_path, built_path, 'build')` — when an `iterate`
  binds a build path to a data path.
- `_register_render_deps(built_bag)` — one edge per `^pointer` in the
  built Bag.

`impacted_builders(changed_paths)` walks the graph, following `formula`
edges transitively (pull cascade) and collecting terminal edges (render
or build) keyed by `builder_name`. Per builder, `build` wins over
`render`.

### 11.5 `RenderTarget` and throttling

[src/genro_builders/render_target.py](../../src/genro_builders/render_target.py)
defines the abstraction:

```python
class RenderTarget:
    def write(self, content: str) -> Any: ...

class FileRenderTarget(RenderTarget):
    def __init__(self, path: str | Path) -> None: ...
    def write(self, content: str) -> None: ...
```

The manager wires targets via:

```python
manager.set_render_target(
    "page", "html",
    target=FileRenderTarget("out/page.html"),
    min_interval=1.0,
)
```

`min_interval` is throttled per (builder, renderer): a render within
`min_interval` seconds of the previous one is skipped.

### 11.6 `FormulaResolver.on_loading`

At load time, the resolver hook receives `kw` and rewrites pointer
kwargs:

```python
def on_loading(self, kw):
    for name, value in kw.items():
        if is_pointer(value):
            abs_path = self._built_context.abs_datapath(value[1:])
            kw[name] = self._data_bag.get_item(abs_path)
    return kw
```

The resolution uses the **same** `abs_datapath` the system uses
everywhere else. The target architecture's "no prepend, no fallback"
rule propagates all the way into formulas — what you wrote is what
you read.

### 11.7 Reactive dispatch — sequence diagram

```{mermaid}
sequenceDiagram
    participant UI as User / ASGI
    participant LS as local_store (Bag)
    participant M as ReactiveManager
    participant DG as DependencyGraph
    participant B as Builder
    participant T as RenderTarget

    UI->>LS: set_item("x", v)
    LS-->>M: subscriber("x changed")
    M->>M: _pending_changes.append("x")
    M->>M: loop.call_soon(_flush)
    Note over M: next tick
    M->>DG: impacted_builders(["x"])
    DG-->>M: {"page": "render"}
    M->>B: render(name="html")
    B-->>M: "<html>...</html>"
    M->>T: write("<html>...</html>")
```

### 11.8 Async considerations

- `build()` and `run()` return a coroutine if any builder's build is
  async; otherwise `None`. `smartawait` smooths over the two worlds.
- `_interval` (active cache) requires a running loop to tick.
- `subscribe()` works in sync too, but then `_flush` runs synchronously
  the moment a change happens (no coalescing across ticks).

---

## 12. Render and Compile

### 12.1 Render

`BagRendererBase` (in `genro_builders.renderer`) provides the walk
(`_walk_render`) and dispatch (`_dispatch_render`). Subclasses override
**only** `render_node(node, parent, **kw)`. Tag-specific overrides use
`@renderer` (template-driven or imperative).

```python
class MyRenderer(BagRendererBase):
    def render_node(self, node, parent=None, **kw):
        tag = node.node_tag or node.label
        attrs = {k: v for k, v in node.runtime_attrs.items() if not k.startswith("_")}
        value = node.runtime_value
        ...
```

Two properties carry the resolved view of the node:

- `node.runtime_value` — pointer + callable resolved.
- `node.runtime_attrs` — all attributes resolved, `datapath` and
  callable defaults handled.

### 12.2 Compile

`BagCompilerBase` is the compiler twin. It is **top-down**: the handler
for a node runs first and returns an object; if the node has children,
they are compiled with that object as their parent.

Use `@compiler` for tag-specific handlers.

### 12.3 Resolution invariant

Pointer resolution **lives on the node**. Renderers and compilers only
call `runtime_value` / `runtime_attrs`. This is the single place that
evaluates `^pointer` / callable attributes. Any other code that dares
read `node.attr["x"]` and interpret `^...` itself is wrong.

### 12.4 Rendering the same built multiple times

Because the built Bag is purely formal, the same tree can be rendered
multiple times against different local_store snapshots, producing
different outputs. The reactive dispatch exploits this: rebuild is rare,
re-render is common.

---

## 13. Invariants and Contracts (the "a prova di bomba" checklist)

A system is robust when its invariants are loud and enforced. The
following items are the load-bearing ones.

| # | Invariant | Enforced by | Violation mode |
|---|-----------|-------------|----------------|
| 1 | **Local isolation** — a builder never reads or writes another builder's local_store except through `volume:path`. | `abs_datapath`, manager registry | `KeyError` on missing volume; `ValueError` on unresolved relative |
| 2 | **No prepend** — no code inserts a builder name into any path. | `abs_datapath` (no prefix logic) | Inconsistent reads, formula leaks |
| 3 | **No silent fallback** — unresolvable paths raise, never return default. | `abs_datapath` explicit `raise ValueError` | `ValueError` |
| 4 | **Single-root component** — a component produces exactly one top-level node, matching its declared `main_tag` (if any). | `_validate_component_tree` | `ValueError` at build |
| 5 | **Built is formal** — `^pointer` strings are never resolved at build time. | `_build_walk` (materializes without resolving) | Subtle bugs in snapshot rendering |
| 6 | **Resolution on node** — only `BuiltBagNode` resolves `^pointer`. | `runtime_value`, `runtime_attrs` | Divergent outputs |
| 7 | **Pull-based formulas** — `data_formula` is always on-demand; no proactive push. | `FormulaResolver(BagSyncResolver)` | Cascades not converging |
| 8 | **Volume is the only cross-builder vehicle** — no manager/builder back-channels in user code. | Convention; reviewed in PRs | Hidden coupling |
| 9 | **DataBuilder for shared data** — shared data lives in a `DataBuilder`, never in presenter builders. | Convention; `HtmlManager` nudges it | Ownership confusion |
| 10 | **Manager is registry** — the manager does not own data; it registers builders and resolves volumes. | `BuilderManager.register_builder` / `local_store` | N/A if respected |
| 11 | **Datapath uses pointer grammar** — `datapath` accepts every form a `^pointer` body accepts: plain, relative, volume (`x:y`), symbolic (`#id.rest`), volume + symbolic (`x:#id.rest`). | `_resolve_datapath` + `abs_datapath` | Silent misread on reset / cross-volume chains |
| 12 | **Single data access channel** — every read from / write to the data store goes through `node.get_relative_data(path)` and `node.set_relative_data(path, value)`. Scalar dereferencing uses `node.current_from_datasource(value)` (§10.7), which composes on top of `get_relative_data`. Direct `data.get_item` / `data.set_item` calls, *and* hand-rolled `abs_datapath(...)` + read/write sequences, from builder, build, output, formula or reactive code are forbidden. `abs_datapath` is a low-level primitive (§6.2), not an application entry point. | Code review; future lint | Divergent resolution rules, missing anti-loop, broken volume routing |
| 13 | **One resolver, not two** — `abs_datapath` is the single path-resolution primitive. The former `_resolve_datapath` is absorbed as an internal step of `abs_datapath`. No code — internal or external — calls `_resolve_datapath` as a standalone entry. | `abs_datapath` implementation | Parallel resolution paths that drift |

---

## 14. Migration — What Must Die

> **Status (Tranche A + B + C complete)**: items 1–8, 12 and 13 are
> done. Items 9–11 remain partial — see the per-item notes.

The working tree at commit `1a5cab3` still contained automatisms that
the target architecture forbids. The list below is preserved for
historical reference; each item is annotated with its current status.

1. ✅ **Done (Tranche A)**: prepend of `builder_name` in
   `BuiltBagNode.abs_datapath` removed.
2. ✅ **Done (Tranche A)**: prepend of `builder_name` in
   `BuilderBagNode.abs_datapath` removed.
3. ✅ **Done (Tranche A)**: `BuilderBagNode._find_builder_name()` removed.
4. ✅ **Done (Tranche A)**: docstrings cleaned up.
5. ✅ **Done (Tranche B)**: `BuilderManager._data` removed; replaced
   with a `{name: builder._data}` registry in `self._stores`.
6. ✅ **Done (Tranche B)**: `global_store` property removed (hard break).
7. ✅ **Done (Tranche B)**: `register_builder` no longer creates a
   `Bag()` namespace — it records a reference to the builder's
   private `_data`.
8. ✅ **Done (Tranche B)**: `data_setter` and `data_formula` route
   writes through `set_relative_data` / `set_resolver` on the
   resolved target Bag (own local_store or remote volume).
9. Tests assuming `global_store["page.xxx"]`:
   `tests/test_main_store.py`,
   `tests/test_build_e2e.py::test_per_row_formula_values`,
   `tests/test_abs_datapath.py` — rewrite to use `app.page.data["xxx"]`
   and to assert the `ValueError` paths.
10. Documentation: `docs/builders/contract.md` section on data store,
    and every example in `contrib/html/examples/` that implicitly
    relies on prepend.
11. `_resolve_datapath` (in both `BuiltBagNode` and `BuilderBagNode`)
    currently treats the `datapath` attribute as an opaque string: it
    only distinguishes "starts with `.`" (relative → concatenate) from
    "otherwise" (absolute → break). It does **not** resolve `volume:`
    (propagation into the cross-builder store) and it does **not**
    resolve `#node_id` (symbolic lookup). For invariant 11 to hold,
    `_resolve_datapath` + `abs_datapath` must be taught to handle the
    five canonical forms listed in §6.1 (plain, relative, volume,
    symbolic, volume + symbolic), with the symbolic branch routed
    through `node_by_id` (source side) and erroring cleanly on the
    built side, where no id map exists.
12. ✅ **Done (Tranche B + partial C)**: every applicative read/write
    flows through `node.get_relative_data` / `node.set_relative_data`.

    Migrated:
    - `_execute_data_setter` ([src/genro_builders/builder/_build.py](../../src/genro_builders/builder/_build.py)):
      now calls `context_node.set_relative_data(raw_path, value)`.
    - `_install_formula_resolver` ([src/genro_builders/builder/_build.py](../../src/genro_builders/builder/_build.py)):
      installs the resolver on the target Bag returned by
      `context_node._resolve_target_bag(resolved_path)` (volume-aware).
    - `_on_built` warm-up: stores `(target_bag, local_path)` and reads
      `target_bag.get_item(local_path)` — volume-aware.
    - `_expand_component_iterate`: reads via
      `node.get_relative_data(raw_path)`.
    - `BuilderBagNode.current_from_datasource`: now a one-liner that
      delegates to `self.get_relative_data(value[1:])`.
    - `FormulaResolver.on_loading`: resolves dependency pointers via
      `ctx.get_relative_data(value[1:])`. The `_data_bag` field is gone.

    Legitimate remaining callers of `abs_datapath` (no read, no write —
    just a path string for the dependency graph):
    `_register_dep`, `_register_render_deps`, `_register_formula_deps`.

13. ✅ **Done (Tranche C final)**: `_resolve_datapath` renamed to
    `_walk_ancestor_datapath` in both
    [src/genro_builders/built_bag.py](../../src/genro_builders/built_bag.py)
    and [src/genro_builders/builder_bag.py](../../src/genro_builders/builder_bag.py).
    The helper is now clearly private; ``abs_datapath`` is the only
    primitive in the public API surface. The dead-code wrapper
    ``BuilderBagNode._resolve_path`` was removed at the same time.

---

## 15. Glossary

| Term | Meaning |
|------|---------|
| **source** | The `BuilderBag` populated by `main()`. The recipe. |
| **built** | The `BuiltBag` produced by `build()`. Components expanded, elements materialized, `^pointer` verbatim. |
| **local_store** | The data Bag owned by a builder. Accessed as `builder.data`. Also referenced by volume name in the manager. |
| **volume** | A builder name acting as a namespace for cross-builder reads, via `^name:path`. |
| **datapath** | A node attribute that sets the data context for the node and its descendants. Composed via ancestor walk. |
| **anchor** | The closest absolute `datapath` found while walking ancestors. Required to resolve relative pointers. |
| **pointer** | A `^...` string carrying a data path reference. Resolved on demand on the built side. |
| **node_id** | A source-side stable identifier used by the symbolic pointer form `#node_id.field`. |
| **DataBuilder** | A builder with no renderer/compiler, dedicated to describing shared data schemas. |
| **DependencyGraph** | The inverse index `{data_path: [edges]}` built during `build()`; drives reactive dispatch. |

---

## 16. Appendix A — File Map

| File | Purpose |
|------|---------|
| [src/genro_builders/builder/base.py](../../src/genro_builders/builder/base.py) | `BagBuilderBase` — init, pipeline properties, `on_configure`. |
| [src/genro_builders/builder/_grammar.py](../../src/genro_builders/builder/_grammar.py) | Grammar dispatch, schema introspection. |
| [src/genro_builders/builder/_build.py](../../src/genro_builders/builder/_build.py) | Build walk, phase 2, dependency registration. |
| [src/genro_builders/builder/_component.py](../../src/genro_builders/builder/_component.py) | `ComponentProxy`, component mixin. |
| [src/genro_builders/builder/_output.py](../../src/genro_builders/builder/_output.py) | `render`, `compile`, check/validate. |
| [src/genro_builders/builder/_reactivity.py](../../src/genro_builders/builder/_reactivity.py) | `ReactivityEngine` (per-builder). |
| [src/genro_builders/builder/_binding.py](../../src/genro_builders/builder/_binding.py) | Pointer parsing, `BindingManager`. |
| [src/genro_builders/builder_bag.py](../../src/genro_builders/builder_bag.py) | `BuilderBag`, `BuilderBagNode`, source-side `abs_datapath`. |
| [src/genro_builders/built_bag.py](../../src/genro_builders/built_bag.py) | `BuiltBag`, `BuiltBagNode`, built-side `abs_datapath`, `runtime_value`, `runtime_attrs`. |
| [src/genro_builders/formula_resolver.py](../../src/genro_builders/formula_resolver.py) | `FormulaResolver` with `on_loading`. |
| [src/genro_builders/manager.py](../../src/genro_builders/manager.py) | `BuilderManager`, `ReactiveManager`, `set_render_target`. |
| [src/genro_builders/dependency_graph.py](../../src/genro_builders/dependency_graph.py) | `DepEdge`, `DependencyGraph`. |
| [src/genro_builders/render_target.py](../../src/genro_builders/render_target.py) | `RenderTarget`, `FileRenderTarget`. |
| [src/genro_builders/contrib/data/data_builder.py](../../src/genro_builders/contrib/data/data_builder.py) | `DataBuilder`, `field` element. |
| [src/genro_builders/contrib/html/__init__.py](../../src/genro_builders/contrib/html/__init__.py) | `HtmlManager` batteries-included pair. |

---

## 17. Appendix B — Typical Flows (Mermaid)

### Flow 1 — Single-builder sync

```{mermaid}
flowchart LR
    A["HtmlBuilder()"] --> B["main(source)"]
    B --> C["build()"]
    C --> D["render()"]
```

### Flow 2 — Multi-builder with DataBuilder

```{mermaid}
flowchart TB
    A["App(BuilderManager)"] --> B["on_init: register_builder('data', DataBuilder)"]
    B --> C["register_builder('page', HtmlBuilder)"]
    A --> D["setup(): main_data + main_page"]
    D --> E["build(): data first, then page"]
    E --> F["render page"]
```

### Flow 3 — Relative pointer resolution

```{mermaid}
flowchart TB
    P["p(value='^.name')"] --> R["abs_datapath('.name')"]
    R --> W["walk ancestors collecting datapath"]
    W --> C{"anchor found?"}
    C -->|yes| O["return 'users.0.name'"]
    C -->|no|  V["raise ValueError"]
```

### Flow 4 — Volume resolution

```{mermaid}
flowchart TB
    P["p(value='^data:company')"] --> X["parse_pointer"]
    X --> Y["volume='data', path='company'"]
    Y --> Z["manager.resolve_volume('data') → data.local_store"]
    Z --> G["data.local_store.get_item('company')"]
```

### Flow 5 — Reactive dispatch end-to-end

```{mermaid}
sequenceDiagram
    participant User
    participant Store as local_store
    participant Mgr as ReactiveManager
    participant DG as DependencyGraph
    participant B as page
    participant T as RenderTarget
    User->>Store: set_item("price", 200)
    Store-->>Mgr: subscriber
    Mgr->>Mgr: pending += ["price"]
    Mgr->>Mgr: call_soon(_flush)
    Note over Mgr: next tick
    Mgr->>DG: impacted_builders(["price"])
    DG-->>Mgr: {"page": "render"}
    Mgr->>B: render("html")
    B-->>Mgr: HTML
    Mgr->>T: write(HTML)
```

### Flow 6 — Formula cascade (pull)

```{mermaid}
flowchart LR
    R["read data['quadrupled']"] --> F1["FormulaResolver(quadrupled)"]
    F1 --> R2["read data['doubled']"]
    R2 --> F2["FormulaResolver(doubled)"]
    F2 --> R3["read data['base']"]
    R3 --> V["value"]
```

---

## 18. Appendix C — Quick Reference Card

### Pointer syntax

| Form | Example | Reads |
|------|---------|-------|
| Absolute (current builder) | `^title` | `self.local_store["title"]` |
| Relative | `^.name` | ancestor-resolved path in `self.local_store` |
| Volume | `^data:customer.name` | `data.local_store["customer.name"]` |
| Attribute | `^path?color` | attribute `color` of node at `path` |
| Symbolic (source-side only) | `^#addr.street` | node with `node_id="addr"` + `".street"` |
| Symbolic + volume (source-side) | `^data:#addr.street` | `node_id="addr"` looked up in the `data` builder's source |

### Minimal manager API

```python
manager.register_builder(name, cls, **kw)   # register
manager.local_store(name=None)              # read a builder's local_store
manager.main_<name>(source)                 # populate dispatch
manager.setup()                             # all main_* + main
manager.build()                             # build all
manager.run()                               # setup + build
```

### Reactive manager additions

```python
rmgr.subscribe()                                        # enable reactivity
rmgr.set_render_target(name, renderer,
                       target=FileRenderTarget("x"),
                       min_interval=1.0)
rmgr.on_data_changed(impacted: dict[str, str])          # override for custom dispatch
```

### Error modes to expect

| Error | Where | Meaning |
|-------|-------|---------|
| `ValueError: Unresolved relative datapath` | `BuiltBagNode.abs_datapath` | A relative pointer has no ancestor anchor. |
| `ValueError: Component '<x>' must produce a single top-level node` | `_validate_component_tree` | Component produced a forest. |
| `ValueError: Component '<x>' declared main_tag='y' but produced ...` | `_validate_component_tree` | Component's root tag does not match the declared `main_tag`. |
| `KeyError: Builder '<volume>' not registered` | `local_store` / volume resolution | The volume name is unknown to the manager. |
| `KeyError: No node with node_id '<id>'` | `node_by_id` (source-side symbolic) | Unknown `node_id`. |

---

**End of document.**
