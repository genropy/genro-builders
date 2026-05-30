# Decorators

**Last Updated**: 2026-05-30
**Status**: 🟢 APPROVATO — allineato al contratto v0.5.0 (renderer-side chain landed 2026-05-30).

The framework provides four decorators for declaring a grammar.
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
| `@data_element` | Declare a transparent data-handling element. | Required. |

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

Declares a transparent element used for data-handling (writers,
formulas). The body is a preprocessor returning `(path,
attrs_dict)`. Data elements live in the source tree but emit no
markup at render time.

```python
@data_element()
def data_setter(self, path, value=None, **kwargs):
    return path, dict(value=value, **kwargs)
```

> **Status**: the decorator is registered. Consumption is pending
> until the data layer ships (see `roadmap/data-architecture.md`).

## Declarative vs body-bearing

The four decorators split into two families:

- **Declarative**: `@element`, `@abstract`, `@subbuilder` — the
  framework only reads the signature and metadata. The function
  body is discarded; if you write a non-empty body, a warning is
  emitted at class definition time. Use `...` (ellipsis) as the
  body to suppress the warning.
- **Body-bearing**: `@data_element` — the body **must** be real
  code (ellipsis raises `ValueError`). The framework invokes it
  when data elements are consumed (see the status callout above).
