# Builders overview

**Last Updated**: 2026-06-10
**Status**: 🟢 APPROVATO — allineato al contratto v0.8.0.

A builder is a Python class that defines a grammar for a structured
document — HTML, SVG, CSS, or any user-defined dialect — and IS the
document: it owns the source bag and the create/render lifecycle.

## The three objects

The framework is built around three concrete classes:

- **Builder** (`HtmlBuilder`, `SvgBuilder`, `CssBuilder`, ...) —
  declares the grammar via decorators AND carries the document: a
  mount `name`, the `source` bag, `create()`/`render()`, the render
  targets. A page is a builder subclass with `main(self, root)`.
- **Renderer** (`HtmlRenderer`, `SvgRenderer`, `CssRenderer`, ...) —
  walks the source bag and emits a string. Exposed as
  `renderer_<mode>` properties on the builder class; instances are
  fresh and ephemeral (one `render()` call each).
- **BuilderHandler** — the data source. One segmented datastore that
  mounts N builders by name (`add_builder`), hands each its own data
  segment (`_` is the shared one), tracks readers (`pointer_map`) and
  owns the `live()` mutation section. Only needed when the page reads
  data; it is not subclassed.

## The two phases

The builder's lifecycle has two phases, called explicitly:

```python
page = MyPage()
page.create()  # setup(data) + main(source) + first calculation
page.render()  # serializes source
```

| Phase | Method | What it does |
|-------|--------|--------------|
| Create | `page.create()` | Calls `setup(self.data)` (seed the data), then `self.main(self.source)` (user code populates the source bag), then the first calculation of the data-elements. |
| Render | `page.render(mode=None, target=None, validate=True, **opts)` | Walks the source via `renderer_<mode>`. Returns the serialized output, or writes it to a target (argument, or registered via `page.set_render_target(target)`). The walk checks minimum child cardinality; `validate=False` deliberately emits a partial document. |

The source bag is inspectable as `page.source` after `create()`.

With data, the handler mounts and creates the page:

```python
page = CustomerPage(name="customer")
handler = BuilderHandler()
handler.add_builder(page)   # mounts under page.name, calls create()
page.render()
```

## Grammar declaration

A builder declares its grammar via decorators on methods:

```python
from genro_builders.builder import BuilderBase, element

class MyBuilder(BuilderBase):

    @element(sub_tags='body')
    def html(self): ...

    @element(sub_tags='h1,p[]')
    def body(self): ...

    @element(sub_tags='')   # leaf (void element)
    def br(self): ...
```

An unknown item in `sub_tags` raises at class definition time. See
[Decorators](decorators.md) for the full list.

## Page subclassing

The user defines the page by subclassing the dialect builder and
overriding `main` (and `setup` when the page reads data):

```python
from genro_builders.contrib.html import HtmlBuilder

class CustomerPage(HtmlBuilder):
    def main(self, root):
        root.body().h1("Customer page")
```

## What lives where

| Concern | Owned by |
|---------|----------|
| Grammar (tags, validation, schema) | Builder class |
| Source bag (the recipe) | Builder instance (`page.source`, under the structural `_root_`) |
| Rendering (string output) | Renderer (`renderer_<mode>` property, fresh per call) |
| Render targets (file, stream, callable; per mode) | Builder instance |
| Node lookup by id | Builder (`node_by_id`, per-builder namespace) |
| Data (segmented datastore, `_` shared segment) | BuilderHandler |
| Pointer tracking, `live()` mutation section | BuilderHandler |

This separation is fixed by the architecture contract (areas
`BLD` / `PAG` / `HND`). See `roadmap/architecture-contract.md`.

## What is here, and what is next

Already implemented:

- **Pull-based binding** — `^pointer` / `=pointer` / `${name}` resolved
  at render time, with read-time pointer registration (`DAT.2`); data
  presentation via `mask`/`_wdg` (`DAT.5`); consumed template inputs
  (`DAT.6`).
- **Data-elements** — `data_setter`, `data_formula`, `data_controller`
  (plain `@element` marked as data), first calculation during
  `create()`, single-wave recompute on mutation (`DAT.4`). See
  [Decorators](decorators.md).
- **Multibuilder** — N pages on one handler, segmented data (`HND`).
- **Push reactivity, Level 0** — with an application, inside
  `with handler.live():` every mutation queues a render flushed at
  the section exit (`RX.1`).

Designed but not yet implemented:

- **Components** (`CMP`) and **`@slot`** (`PAG.6`) — named reusable
  structures with render-time expansion; fill-by-id at node birth.
  See `roadmap/component-design.md`.
- **Data-element cascade (slice 2)** — multi-wave re-firing (`DAT.4`).
- **Finer-grained push reactivity** — partial render in the `live()`
  flush, SRC/DATA granularity (`RX`).
