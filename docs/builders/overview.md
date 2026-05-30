# Builders overview

**Last Updated**: 2026-05-30
**Status**: 🟡 APPROVATO PARZIALMENTE — header bumped to v0.5.0; contenuto da rileggere contro la catena renderer-side.

A builder is a Python class that defines a grammar for a structured
document: HTML, SVG, CSS, or any user-defined dialect.

## The three objects

The framework is built around three concrete classes:

- **Builder** (`HtmlBuilder`, `SvgBuilder`, `CssBuilder`, ...) —
  declares the grammar via decorators. No runtime state. No
  rendering logic.
- **Renderer** (`HtmlRenderer`, `SvgRenderer`, `CssRenderer`, ...) —
  walks the source bag and emits a string. One renderer class per
  grammar, one renderer instance per mode.
- **Handler** (`HtmlBuilderHandler`, `SvgBuilderHandler`,
  `CssBuilderHandler`, ...) — the engine. Owns one builder instance,
  one source bag, and a mode-keyed dict of render targets. Drives
  the lifecycle.

The user subclasses the handler and implements `main(self, root)`.

## The two phases

The handler's lifecycle has two phases, called explicitly:

```python
page = MyPage()
page.create()  # main(source) populates self.source
page.render()  # serializes source
```

| Phase | Method | What it does |
|-------|--------|--------------|
| Create | `handler.create()` | Calls `self.main(self.source)`. User code runs here, populating the source bag. |
| Render | `handler.render(mode=None, target=None, **kwargs)` | Dispatches to the renderer registered for `mode`. Returns the serialized output, or writes it to a render target previously registered via `handler.set_render_target(mode, target)`. |

The source bag is inspectable as `page.source` after `create()`.

## Grammar declaration

A builder declares its grammar via decorators on methods:

```python
from genro_builders.builder import BagBuilderBase, element

class MyBuilder(BagBuilderBase):

    @element(sub_tags='body')
    def html(self): ...

    @element(sub_tags='h1,p[]')
    def body(self): ...

    @element(sub_tags='')   # leaf (void element)
    def br(self): ...
```

See [Decorators](decorators.md) for the full list.

## Handler subclassing

The user defines the handler subclass by overriding `main`:

```python
from genro_builders.contrib.html import HtmlBuilderHandler

class CustomerPage(HtmlBuilderHandler):
    def main(self, root):
        root.body().h1("Customer page")
```

`HtmlBuilderHandler` has its `builder_class` already set to
`HtmlBuilder`. The user only writes `main`.

## What lives where

| Concern | Owned by |
|---------|----------|
| Grammar (tags, validation, schema) | Builder |
| Source bag (the recipe) | Handler |
| Rendering (string output) | Renderer (one per mode, instantiated lazily by handler) |
| Render targets (file, stream, buffer; one per mode) | Handler |
| Node lookup by id | Handler (`node_by_id`) |

This separation is fixed by the architecture contract (sections
`BLD.3` / `HND.3`, v0.5.0). See `roadmap/architecture-contract.md`.

## What is not yet here

The following features are designed but not yet implemented:

- **Data and pointers** (`handler.data`, `^pointer`, `datapath`).
  See `roadmap/data-architecture.md`.
- **Reactivity** — automatic re-render when data changes. See
  `roadmap/implementation-roadmap.md`.
- **Sub-builders** (`@subbuilder(OtherBuilder)`). Decorator
  registers in the schema; attach logic is under active development
  (see `temp/subtask/subbuilder/`).
