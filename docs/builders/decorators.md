# Decorators

**Version**: 0.1.0
**Last Updated**: 2026-05-14
**Status**: 🔴 DA REVISIONARE — Documento non ancora approvato.

The framework provides five decorators for declaring a grammar.
They live in
[src/genro_builders/builder/_decorators.py](../../src/genro_builders/builder/_decorators.py)
and are imported as:

```python
from genro_builders.builder import (
    element, abstract, subbuilder, component, data_element,
)
```

## At a glance

| Decorator | Purpose | Body |
|-----------|---------|------|
| `@element` | Declare a tag in the grammar. | Ignored (declarative). |
| `@abstract` | Declare an abstract base for inheritance. | Ignored (declarative). |
| `@subbuilder` | Open a sub-grammar from this tag down. | Ignored (declarative). |
| `@component` | Declare a macro that expands at build time. | Required. |
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

@element(inherits_from='@phrasing')
def p(self): ...
```

Abstracts are stored under their name prefixed with `@`. The
concrete element references them via `inherits_from='@<name>'`.

## `@subbuilder`

Marks a tag as the entry point for a different grammar.

```python
class HtmlBuilder(BagBuilderBase):

    @subbuilder(SvgBuilder)
    def svg(self): ...
```

From `<svg>` down, the active builder becomes `SvgBuilder`. The
sub-builder governs its own `sub_tags`; the host only declares
`parent_tags` (where the sub-builder may appear).

> **Status**: the decorator and schema collection are in place. The
> attach-time switch of the active `_builder` is under active
> development (see `temp/subtask/subbuilder/`). Until that lands,
> the framework raises `NotImplementedError` when a subbuilder tag
> is encountered.

## `@component`

Declares a macro that produces a sub-tree at build time. The body
**is** executed (one of two body-bearing decorators).

```python
@component(main_tag='div')
def card(self, comp, title, body):
    comp.div(_class="card")
    comp.h2(title)
    comp.p(body)
```

- `main_tag` — the DOM tag this component represents for the
  purpose of parent-side `sub_tags` validation.
- `sub_tags` — what the component accepts as children **after**
  creation (`''` = closed, anything else = open container).
- `slots` — named slots that callers can fill from outside.

> **Status**: the decorator is registered in the schema. Build-time
> expansion is pending (see `roadmap/architecture-contract.md` §7).

## `@data_element`

Declares a transparent element used for data-handling (writers,
formulas). The body is a preprocessor returning `(path,
attrs_dict)`. Data elements do not appear as nodes in the built bag.

```python
@data_element()
def data_setter(self, path, value=None, **kwargs):
    return path, dict(value=value, **kwargs)
```

> **Status**: the decorator is registered. Build-time consumption is
> pending until the data layer ships (see
> `roadmap/data-architecture.md`).

## Declarative vs body-bearing

The five decorators split into two families:

- **Declarative**: `@element`, `@abstract`, `@subbuilder` — the
  framework only reads the signature and metadata. The function
  body is discarded; if you write a non-empty body, a warning is
  emitted at class definition time. Use `...` (ellipsis) as the
  body to suppress the warning.
- **Body-bearing**: `@component`, `@data_element` — the framework
  invokes the function during build. The body **must** be real
  code (ellipsis raises `ValueError`).
