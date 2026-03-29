# genro-builders

Builder system for [genro-bag](https://github.com/genropy/genro-bag) — grammar, validation, compilation, and reactive data binding.

## Installation

```bash
pip install genro-builders
```

## Quick start

```python
from genro_builders.builders import HtmlBuilder

builder = HtmlBuilder()
body = builder.source.body()
body.div(id='main').p('Hello, world!')

builder.build()
print(builder.output)
```

## Features

- **Domain-specific grammars** — Define elements, validation rules, and components via decorators (`@element`, `@abstract`, `@component`)
- **Named slots** — Components can declare insertion points (`slots=['left', 'right']`) for user content injection at recipe time
- **Built-in builders** — HTML5, Markdown, XSD (schema-driven XML)
- **Reactive pipeline** — Build source, resolve `^pointer` bindings, render output. Data changes trigger automatic re-render
- **Multi-builder coordination** — `BuilderManager` mixin coordinates multiple builders with a shared data bus
- **Validation** — `sub_tags` cardinality, `parent_tags` constraints, typed attribute validation

## Architecture

A builder owns the full pipeline:

```text
builder.source  (recipe: builder calls, components, ^pointer strings)
    ↓ builder.build()
builder.built  (components expanded, ^pointers resolved, subscriptions active)
    ↓ compiler.render()
builder.output  (HTML, Markdown, XML, ...)
```

Data changes trigger automatic updates via the `BindingManager` subscription map.

## Documentation

See the [docs/](docs/) directory for full documentation.

## License

Apache License 2.0 — Copyright 2025 Softwell S.r.l.
