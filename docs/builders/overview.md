# Builders overview

**Version**: 0.1.0
**Last Updated**: 2026-05-14
**Status**: 🔴 DA REVISIONARE — Documento non ancora approvato.

A builder is a Python class that defines a grammar for a structured
document: HTML, SVG, CSS, or any user-defined dialect.

## The three objects

The framework is built around three concrete classes:

- **Builder** (`HtmlBuilder`, `SvgBuilder`, `CssBuilder`, ...) —
  declares the grammar via decorators. No runtime state. No
  rendering logic.
- **Renderer** (`HtmlRenderer`, `SvgRenderer`, `CssRenderer`, ...) —
  walks a built bag and emits a string. One renderer class per
  grammar.
- **Handler** (`HtmlBuilderHandler`, `SvgBuilderHandler`,
  `CssBuilderHandler`, ...) — the engine. Owns one builder instance,
  one source bag, one built bag, one render target. Drives the
  lifecycle.

The user subclasses the handler and implements `main(self, root)`.

## The three phases

The handler's lifecycle has three phases, called explicitly:

```python
page = MyPage()
page.create()  # main(source) populates self.source
page.build()   # source → built (expands components, etc.)
page.render()  # serializes built
```

| Phase | Method | What it does |
|-------|--------|--------------|
| Create | `handler.create()` | Calls `self.main(self.source)`. User code runs here, populating the source bag. |
| Build | `handler.build()` | Walks the source and produces the built bag. For plain HTML/SVG/CSS this is mostly a mirror. Future expansion: components, data elements. |
| Render | `handler.render(mode=None, **kwargs)` | Dispatches to `handler.renderer.render_<mode>(...)`. Returns the serialized output or writes it to `handler.render_target`. |

Each phase is independently inspectable: `page.source` after
`create()`, `page.built` after `build()`.

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
| Built bag (the materialized tree) | Handler |
| Rendering (string output) | Renderer (instantiated lazily by handler) |
| Compilation (future: live objects) | Compiler (stub; `NotImplementedError`) |
| Render target (file, stream, buffer) | Handler |
| Node lookup by id | Handler (`node_by_id`) |

This separation is fixed by the architecture contract (decision 8,
renegotiated 2026-05-12). See `roadmap/architecture-contract.md`.

## What is not yet here

The following features are designed but not yet implemented:

- **Data and pointers** (`handler.data`, `^pointer`, `datapath`).
  See `roadmap/data-architecture.md`.
- **Reactivity** — automatic re-render when data changes. See
  `roadmap/implementation-roadmap.md`.
- **Compilers** — concrete `compile()` methods. Today every
  `*.compiler` is a stub that raises `NotImplementedError`.
- **Components** (`@component` expansion in build). The decorator is
  registered in the schema; expansion logic is pending.
- **Sub-builders** (`@subbuilder(OtherBuilder)`). Decorator
  registers in the schema; attach logic is under active development
  (see `temp/subtask/subbuilder/`).
