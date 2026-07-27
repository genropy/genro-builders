# Builders overview

**Last Updated**: 2026-07-27
**Status**: 🟢 APPROVATO — allineato al contratto v0.9.0.

A builder is a Python class that defines a grammar for a structured
document — HTML, SVG, CSS, or any user-defined dialect — and IS the
document: it owns the source bag and the create/render lifecycle.

## The three objects

The framework is built around three concrete classes:

- **Builder** (`HtmlBuilder`, `SvgBuilder`, `CssBuilder`, ...) —
  declares the grammar via decorators AND carries the document: a
  `name` (a label, not an address), the `source` bag,
  `create()`/`render()`, the render targets. A page is a builder
  subclass with `main(self, root)`.
- **Renderer** (`HtmlRenderer`, `SvgRenderer`, `CssRenderer`, ...) —
  walks the source bag and emits a string. Exposed as
  `renderer_<mode>` properties on the builder class; instances are
  fresh and ephemeral (one `render()` call each).
- **BuilderHandler** — the data source. It mounts ONE builder
  (`add_builder`) on one FLAT datastore — absolute paths with no leading
  segment — and tracks readers (`pointer_map`). It does not render. Only
  needed when the page reads data; it is not subclassed.

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
| Render | `page.render(mode=None, target=None, **opts)` | Walks the source via `renderer_<mode>`. Returns the serialized output, or writes it to a target (argument, or registered via `page.set_render_target(target)`). Composes two steps, both callable alone: `page.materialize(mode)` walks and keeps the result in `page.materialized[mode]`, `finalize` delivers it. |
| Validate | `page.validate_source()` | Reports the nodes whose minimum child cardinality is unmet: `(fullpath, [missing tags])` per node, empty list when the document is complete. Rendering never implies it — the author asks. |

The source bag is inspectable as `page.source` after `create()`.

With data, the handler mounts and creates the page:

```python
page = CustomerPage(name="customer")
handler = BuilderHandler()
handler.add_builder(page)   # mounts the page, calls create()
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
| Data (one flat datastore, no segments) | BuilderHandler |
| Pointer tracking (`pointer_map`) | BuilderHandler |

This separation is fixed by the architecture contract (areas
`BLD` / `PAG` / `HND`). See `roadmap/architecture-contract.md`.

## What is here, and what is next

Already implemented:

- **Pull-based binding** — `^pointer` / `=pointer` / `${name}` resolved
  at render time, with read-time pointer registration (`DAT.2`); data
  presentation via `mask`/`_wdg` (`DAT.5`); consumed template inputs
  (`DAT.6`).
- **Data-elements** — `dataSetter`, `dataFormula`, `dataController`
  (plain `@element` marked as data). All three compute during `create()`,
  once, in document order: see [Decorators](decorators.md).
- **Components** — `@component` (render-time ephemeral expansion,
  `iterate` over a collection) and `@container` (generates real source
  at call time). See [Components](components.md).

Designed but not yet implemented:

- **`@slot`** (`PAG.6`) — fill-by-id at node birth. See
  `roadmap/component-design.md`.
- **Reactivity** — the document is static: a data change is followed by
  rendering again. Fine-grained reactivity is a separate engine (`RX`),
  still under design, not this handler.
