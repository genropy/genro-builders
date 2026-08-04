# Decorators

**Last Updated**: 2026-07-27
**Status**: 🟢 APPROVATO — allineato al contratto v0.9.0.

The grammar decorators live in
[src/genro_builders/builder/_decorators.py](../../src/genro_builders/builder/_decorators.py)
and are imported as:

```python
from genro_builders.builder import (
    element, abstract, container, component,
)
```

## At a glance

| Decorator   | Purpose                                    | Body                  |
|-------------|--------------------------------------------|-----------------------|
| `@element`  | Declare a tag in the grammar.              | Ignored (declarative).|
| `@abstract` | Declare an abstract base for inheritance.  | Ignored (declarative).|
| `@container` | A reusable construction block, invocable from a node. | Runs (builds). |
| `@component` | A named grammar element with a body, expanded ephemerally at render time. Bare decorator (no arguments). The element is then *called* in three forms — explicit params, `store`, `iterate`. See [Components](components.md). | Runs (builds). |

There is **no** separate `@subbuilder` or `@data_element` decorator.
Both are ordinary `@element` declarations marked in their `_meta`:

- a **sub-builder** (dialect boundary) is
  `@element(_meta={"subbuilder": "<dialect>", ...})`;
- a **data-element** (`dataSetter`, `dataFormula`, `dataController`)
  is `@element(_meta={"data_element": True})`.

See the dedicated sections below.

## `@element`

Declares a concrete tag. **The tag is the method name** — there is no
`tags` argument.

```python
@element(sub_tags='h1,p')
def body(self): ...

@element(sub_tags='', parent_tags='ul,ol')
def li(self): ...
```

### A tag that is a Python keyword

When the tag clashes with a Python keyword (`del`, `class`, `for`…), name
the method with a trailing underscore: the renderer strips it on emission.

```python
@element(sub_tags='*')
def del_(self): ...        # the markup is <del>...</del>
```

For a tag a method name cannot spell at all — a hyphen or a colon
(`order-line`, `xsl:for-each`) — declare the emitted tag explicitly via
`_meta={'render_tag': '...'}` (see *Sub-builders* below); the method keeps
a valid name, the renderer emits the real tag.

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

`node_label` (optional) — a fixed default label for a singleton element,
so the node is reachable by a stable key instead of an auto-generated one
(`body_0`, `body_1`…). HTML's `body` and `head` use it. The caller's
`node_label=` argument, if given, overrides this default.

```python
@element(sub_tags='...', node_label='body')
def body(self): ...
# page.source['body'] — not 'body_0'
```

`collection_key` (optional) — declares the element a **collection**: each
child is labelled by its natural key instead of an auto-label. The value
is either a child attribute name, or a `${...}` template over child
attributes. It is **strict** — a missing attribute, a duplicate key among
siblings, or an explicit `node_label=` on a child all raise.

```python
@element(sub_tags='database', collection_key='code')
def databases(self): ...

db = root.databases()
db.database(code='maindb', name='abh_878')
db.database(code='logistic', name='logadelby')
# db['maindb'], db['logistic'] — not database_0, database_1

# template form: collection_key='${code}_${env}'  ->  label 'maindb_prod'
```

To point at a default member, pass an ordinary attribute on the
collection node naming the chosen key — there is no special framework
parameter, it is a plain attribute your application reads:

```python
db = root.databases(default='maindb')   # 'default' is just an attribute
# the application reads node.attr['default'] to pick the default member
```

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
contract `BLD.3`), and `get_subbuilder` propagates the datastore to it;
the boundary node may carry a
`render_tag`/`render_attributes` envelope in its `_meta` (e.g. SVG
hosting HTML in `<foreignObject xmlns="...">`).

The marker has a second form, the **parameter reference**
`"kwarg:attr"` (contract `BLD.2`): the grammar of the subtree is not
fixed in the host grammar — it comes from an object the recipe passes
at the call site:

```python
@element(_meta={"subbuilder": "app:grammar"})
def application(self, code=None, app=None): ...
```

*The value passed as `app` carries in `grammar` the mixin class that
governs everything below this node.* The kwarg left unset means no
switch (the node stays a leaf of the host grammar); the referenced
class is fabricated into a builder once and cached. The envelope's own
arguments belong to the **host** grammar — only its children live in
the mounted one. This is the primitive behind the
[config dialect](../grammars/config.md); the runnable example is
`contrib/html/examples/no_data/10_subbuilder_by_reference/`.

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
    def dataSetter(self, destination: str, value: Any): ...

    @element(_meta={"data_element": True})
    def dataFormula(self, destination: str, func: str | Callable, **kwargs): ...

    @element(_meta={"data_element": True})
    def dataController(self, func: str | Callable, **kwargs): ...
```

The **kind is the tag name** (`node.node_tag`); there is no `kind`
parameter. The three kinds differ by graph role and output:

| Tag | Signature | Role |
|-----|-----------|------|
| `dataSetter` | `dataSetter(destination, value)` | seed — writes `value` at `destination` (a `dict`/`Bag` is allowed); runs at create, always |
| `dataFormula` | `dataFormula(destination, func, **bindings)` | computed — writes the return of `func(**bindings)` at `destination`; pure |
| `dataController` | `dataController(func, **bindings)` | side effect — `func(node, **bindings)` may write any number of bag paths; no declared `destination` |

Used near the structure, inside `main()`:

```python
def main(self, root):
    body = root.body(datapath="x")
    body.dataSetter("price", 100)
    body.dataSetter("tax", 0.22)
    body.dataFormula("total", func="compute_total",
                      price="^price", tax="^tax")
    body.p("^total")
```

- **`destination`** (1st field of `dataSetter`/`dataFormula`) — where
  the result goes, absolute or relative (`".total"` is composed via
  `abs_datapath`, like a pointer). `dataController` has no
  `destination`.
- **`value`** (of `dataSetter`) — kept as a flat attribute (not the
  node value), so a `Bag` payload is not captured into the source tree.
- **`func`** — the canonical form is a **`@staticmethod` name**
  (`func="compute_total"`), resolved left-to-right over the builder's
  `data_logic` sources; a miss raises `AttributeError`, a non-static
  match raises `TypeError`. An inline callable is also accepted (handy,
  but makes the page non-serializable and is not cross-language).
- **`bindings`** (kwargs) — the `^pointer` inputs, always explicit,
  resolved via `runtime_values` and passed to `func` **by name**.
  `dataFormula`'s `func` is pure (`func(**bindings)`);
  `dataController`'s receives the node first (`func(node, **bindings)`).

There is no flag to request execution: all three run at `create()`.

At runtime the dispatch goes through the same `_command_on_node` as any
element; `element_call` recognises the `_meta['data_element']` mark, maps
the positional args onto the field names, and flags the node
`_is_data_element` (which the renderer skips).

> **Status**: all three compute at `create()`, once, in **document
> order** — the calculation walks the source tree top to bottom. So the
> datastore is complete before the render starts, and a node may read a
> value a data-element writes further DOWN the page. The destination is
> the builder's own datastore (`page.data`).
>
> It is a single pass and there is no recompute: a formula reading a value
> that another formula writes AFTER it sees the earlier value, silently.
> Ordering the calculations is the author's job. The recompute on a data
> change belongs to the reactive engine, still under design — see the `RX`
> area of the contract and `roadmap/reactivity/data-elements.md`.

## Declarative bodies

Both decorators are **declarative**: the framework only reads the
signature and metadata, the function body is discarded. For
`@element`/`@abstract`, a non-empty body emits a warning at class
definition time — use `...` (ellipsis) as the body to suppress it.
The data-elements and sub-builders, being `@element`, follow the same
rule; their behaviour lives in the builder's compute pass / the
sub-builder dispatch, not in the body. `@container` and
`@component` are the exceptions: they carry a body that builds.
