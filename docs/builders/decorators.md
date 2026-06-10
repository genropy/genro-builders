# Decorators

**Last Updated**: 2026-06-10
**Status**: 🟢 APPROVATO — allineato al contratto v0.8.0.

The grammar decorators live in
[src/genro_builders/builder/_decorators.py](../../src/genro_builders/builder/_decorators.py)
and are imported as:

```python
from genro_builders.builder import (
    element, abstract, struct_method, component,
)
```

## At a glance

| Decorator   | Purpose                                    | Body                  |
|-------------|--------------------------------------------|-----------------------|
| `@element`  | Declare a tag in the grammar.              | Ignored (declarative).|
| `@abstract` | Declare an abstract base for inheritance.  | Ignored (declarative).|
| `@struct_method` | A reusable construction block, invocable from a node. | Runs (builds). |
| `@component` | A named grammar element with a body, expanded at render time. | Runs (builds). **Design landed, expansion not implemented yet** — see `roadmap/component-design.md` and contract area `CMP`. |

There is **no** separate `@subbuilder` or `@data_element` decorator.
Both are ordinary `@element` declarations marked in their `_meta`:

- a **sub-builder** (dialect boundary) is
  `@element(_meta={"subbuilder": "<dialect>", ...})`;
- a **data-element** (`data_setter`, `data_formula`, `data_controller`)
  is `@element(_meta={"data_element": True})`.

See the dedicated sections below.

## `@element`

Declares a concrete tag.

```python
@element(sub_tags='h1,p[]')
def body(self): ...

@element(sub_tags='', parent_tags='ul,ol')
def li(self): ...
```

`sub_tags` syntax:

- `'a,b,c'` — `a`, `b`, `c` each allowed any number of times (0..N).
- `'a[2],b[0:]'` — `a` exactly twice, `b` zero or more times.
- `''` (empty) — leaf, no children allowed (void element).
- `'*'` — any tag allowed (catch-all).

A bare name is unbounded (0..N); the `foo[]` form is **not** valid and
raises `ValueError` — use the plain name `foo` for 0..N, or `foo[n]`
for an exact count.

`parent_tags` (optional) — comma-separated list of valid parents.
The element can only appear under one of these tags.

`inherits_from` — name of an abstract element whose `sub_tags` are
inherited.

`_meta` (optional) — a dict of metadata attached to the schema entry.
The framework reads `_meta["data_element"]` to recognise a data-element
(see below); dialects may carry their own keys.

## `@abstract`

Declares a base for inheritance. Never instantiated directly.

```python
@abstract(sub_tags='span,a,em,strong')
def phrasing(self): ...

@element(inherits_from='phrasing')
def p(self): ...
```

Abstracts live in a dedicated `_abstracts` sub-bag of the class
schema, separate from the top-level elements / subbuilders. Labels are
bare names — no `@` prefix. The concrete element references them via
`inherits_from='<name>'`.

If `inherits_from` names an abstract that does not exist (including
typos in comma-separated lists like `'phrasing,flow'`), a
`ValueError` is raised at class definition time. This catches
mistakes immediately instead of producing elements with silently
missing `sub_tags`.

## Sub-builders

A tag that opens a different grammar is an ordinary `@element` marked
`_meta={"subbuilder": "<dialect>"}` — there is no `@subbuilder`
decorator:

```python
class Html5Extensions:

    @element(_meta={"subbuilder": "svg"})
    def svg(self): ...
```

From `<svg>` down, the active builder becomes the `svg` dialect. The
sub-builder governs its own `sub_tags`; the host only declares
`parent_tags` (where the sub-builder may appear). At render time the
polymorphic dispatch picks the sub-builder's `renderer_<mode>` (see
contract `BLD.3` / `HND.3`); the boundary node may carry a
`render_tag`/`render_attributes` envelope in its `_meta` (e.g. SVG
hosting HTML in `<foreignObject xmlns="...">`).

## Data-elements

Three **transparent** elements live in the source tree but emit **no
markup** at render time. They carry data behaviour (seeding the data
bag, computing, side effects) executed by the builder's compute. They are
declared once on `BuilderBase` as ordinary `@element` marked
`_meta={"data_element": True}` and injected into every dialect's schema
by `__init_subclass__` — so every builder has them without re-declaring:

```python
class BuilderBase(...):

    @element(_meta={"data_element": True})
    def data_setter(self, destination: str, value: Any): ...

    @element(_meta={"data_element": True})
    def data_formula(self, destination: str, func: str | Callable, **kwargs): ...

    @element(_meta={"data_element": True})
    def data_controller(self, func: str | Callable, **kwargs): ...
```

The **kind is the tag name** (`node.node_tag`); there is no `kind`
parameter. The three kinds differ by graph role and output:

| Tag | Signature | Role |
|-----|-----------|------|
| `data_setter` | `data_setter(destination, value)` | seed — writes `value` at `destination` (a `dict`/`Bag` is allowed); runs at create, always |
| `data_formula` | `data_formula(destination, func, **bindings)` | computed — writes the return of `func(**bindings)` at `destination`; pure |
| `data_controller` | `data_controller(func, **bindings)` | side effect — `func(node, **bindings)` may write any number of bag paths; no declared `destination` |

Used near the structure, inside `main()`:

```python
def main(self, root):
    body = root.body(datapath="x")
    body.data_setter("price", 100)
    body.data_setter("tax", 0.22)
    body.data_formula("total", func="compute_total",
                      price="^price", tax="^tax")
    body.p("^total")
```

- **`destination`** (1st field of `data_setter`/`data_formula`) — where
  the result goes, absolute or relative (`".total"` is composed via
  `abs_datapath`, like a pointer). `data_controller` has no
  `destination`.
- **`value`** (of `data_setter`) — kept as a flat attribute (not the
  node value), so a `Bag` payload is not captured into the source tree.
- **`func`** — the canonical form is a **`@staticmethod` name**
  (`func="compute_total"`), resolved left-to-right over the builder's
  `data_logic` sources; a miss raises `AttributeError`, a non-static
  match raises `TypeError`. An inline callable is also accepted (handy,
  but makes the page non-serializable and is not cross-language).
- **`bindings`** (kwargs) — the `^pointer` inputs, always explicit,
  resolved via `runtime_values` and passed to `func` **by name**.
  `data_formula`'s `func` is pure (`func(**bindings)`);
  `data_controller`'s receives the node first (`func(node, **bindings)`).
- **`_on_start`** (formula/controller) — requests execution at the first
  calculation in `create()`; `data_setter` always seeds at create.

At runtime the dispatch goes through the same `_command_on_node` as any
element; `element_call` recognises the `_meta['data_element']` mark, maps
the positional args onto the field names, and flags the node
`_is_data_element` (which the renderer skips).

> **Status**: the data-elements run at first calculation (during
> `create()`) and recompute in a single wave when a dependency mutates
> (contract `DAT.4`, slice 1). The multi-wave cascade (slice 2) is not
> yet implemented — see the `RX` area of the contract and
> `roadmap/reactivity/data-elements.md`.

## Declarative bodies

Both decorators are **declarative**: the framework only reads the
signature and metadata, the function body is discarded. For
`@element`/`@abstract`, a non-empty body emits a warning at class
definition time — use `...` (ellipsis) as the body to suppress it.
The data-elements and sub-builders, being `@element`, follow the same
rule; their behaviour lives in the builder's compute pass / the
sub-builder dispatch, not in the body. `@struct_method` and
`@component` are the exceptions: they carry a body that builds.
