# Decorators

**Last Updated**: 2026-05-30
**Status**: 🟢 APPROVATO — allineato al contratto v0.5.0 (renderer-side chain landed 2026-05-30).

The framework provides five decorators for declaring a grammar.
They live in
[src/genro_builders/builder/_decorators.py](../../src/genro_builders/builder/_decorators.py)
and are imported as:

```python
from genro_builders.builder import (
    element, abstract, subbuilder, data_element,
)
```

## At a glance

| Decorator | Purpose | Body |
|-----------|---------|------|
| `@element` | Declare a tag in the grammar. | Ignored (declarative). |
| `@abstract` | Declare an abstract base for inheritance. | Ignored (declarative). |
| `@subbuilder` | Open a sub-grammar from this tag down. | Ignored (declarative). |
| `@data_element` | Declare a transparent data-element (`data` / `data_formula` / `data_controller`, by method name). | Ignored (declarative). |

## `@element`

Declares a concrete tag.

```python
@element(sub_tags='h1,p[]')
def body(self): ...

@element(sub_tags='', parent_tags='ul,ol')
def li(self): ...
```

`sub_tags` syntax:

- `'a,b,c'` — each of `a`, `b`, `c` exactly once.
- `'a[],b[]'` — `a` and `b` any number of times.
- `'a[2],b[0:]'` — `a` exactly twice, `b` zero or more times.
- `''` (empty) — leaf, no children allowed (void element).
- `'*'` — any tag allowed (catch-all).

`parent_tags` (optional) — comma-separated list of valid parents.
The element can only appear under one of these tags.

`inherits_from` — name of an abstract element whose `sub_tags` are
inherited.

## `@abstract`

Declares a base for inheritance. Never instantiated directly.

```python
@abstract(sub_tags='span,a,em,strong')
def phrasing(self): ...

@element(inherits_from='phrasing')
def p(self): ...
```

Abstracts live in a dedicated `_abstracts` sub-bag of the class
schema, separate from the top-level elements / subbuilders /
data_elements. Labels are bare names — no `@` prefix. The concrete
element references them via `inherits_from='<name>'`.

If `inherits_from` names an abstract that does not exist (including
typos in comma-separated lists like `'phrasing,flow'`), a
`ValueError` is raised at class definition time. This catches
mistakes immediately instead of producing elements with silently
missing `sub_tags`.

## `@subbuilder`

Marks a tag as the entry point for a different grammar.

```python
class HtmlBuilder(BagBuilderBase):

    @subbuilder(SvgBuilder)
    def svg(self): ...
```

From `<svg>` down, the active builder becomes `SvgBuilder`. The
sub-builder governs its own `sub_tags`; the host only declares
`parent_tags` (where the sub-builder may appear). At render time
the polymorphic dispatch picks the sub-builder's `renderer_<mode>`
(see contract `BLD.3` / `HND.3`); the host can wrap the foreign
fragment in a dialect-specific envelope via `wrapper_<sub_name>`
(e.g. SVG hosting HTML in `<foreignObject xmlns="...">`).

## `@data_element`

A single decorator declares **transparent** elements: they live in the
source tree but emit **no markup** at render time. They carry data
behaviour (writing the data bag, computing, side effects) that runs
in the handler — not at definition. Like `@subbuilder`, the body is
**ignored** (autonomous): only `__name__`/`__doc__` are read; the
wrapper calls the grammar's `_attach_data_element` when the element is
written.

The **kind is the decorated method's name** — there is no separate
decorator per kind. The three kinds differ by graph role and output:

| Method | Signature | Role |
|--------|-----------|------|
| `data` | `data(path, value)` | leaf input — writes `value` at `path` (a `dict` becomes a `Bag`); written at create, always |
| `data_formula` | `data_formula(path, func, **bindings)` | computed — writes the return of `func` at `path` |
| `data_controller` | `data_controller(func, **bindings)` | side effect / free writer — `func` may write any number of bag paths itself; no declared output `path` |

```python
class MyBuilder(BagBuilderBase):

    @data_element
    def data(self): ...

    @data_element
    def data_formula(self): ...

    @data_element
    def data_controller(self): ...
```

Used near the structure, inside `main()`:

```python
def main(self, root):
    body = root.body(datapath="x")
    body.data("price", 100)
    body.data("tax", 0.22)
    body.data_formula("total", func="compute_total",
                      price="^price", tax="^tax")
    body.p("^total")
```

- **`path`** (1st positional of `data`/`data_formula`) — where the
  result goes, absolute or relative (`".total"` is composed via
  `abs_datapath`, like a pointer). `data_controller` has no `path`.
- **`func`** — canonical form is a **handler-method name**
  (`func="compute_total"`, resolved via `getattr(self, ...)`); an
  inline callable/lambda is also accepted (handy, but makes the page
  non-serializable).
- **`bindings`** (kwargs) — the `^pointer` inputs, always explicit,
  passed to `func` **by name** (`func(price=..., tax=...)`).
- **`_on_start`** (formula/controller) — requests execution at the
  first render; plain `data` always writes at create.

> **Status**: the three data-elements run at **first render** (during
> `create()`). The cascade that re-fires dependent data-elements on a
> later mutation is not yet implemented — see the `RX` area of the
> contract and `roadmap/reactivity/data-elements.md`.

## Declarative bodies

All five decorators are **declarative**: the framework only reads the
signature and metadata, the function body is discarded. For
`@element`/`@abstract`/`@subbuilder`, a non-empty body emits a warning
at class definition time — use `...` (ellipsis) as the body to
suppress it. The data-elements declared via `@data_element` are
autonomous in the same way: the body is ignored, the behaviour lives
in the handler's data-pass.
