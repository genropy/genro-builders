# genro-builders

Builder system for [genro-bag](https://github.com/genropy/genro-bag) — grammar, validation, compilation, and reactive data binding.

## Installation

```bash
pip install genro-builders
```

## Quick start

```python
from genro_builders import BuilderBag
from genro_builders.builders import HtmlBuilder

html = BuilderBag(builder=HtmlBuilder)
body = html.body()
body.div(id='main').p('Hello, world!')

print(html.builder._compile())
```

## Features

- **Domain-specific grammars** — Define elements, validation rules, and components via decorators (`@element`, `@abstract`, `@component`)
- **Built-in builders** — HTML5, Markdown, XSD (schema-driven XML)
- **Compilation pipeline** — Expand components, resolve `^pointer` bindings, render output
- **Reactive applications** — `BagAppBase` provides automatic re-render on data or source changes
- **Validation** — `sub_tags` cardinality, `parent_tags` constraints, typed attribute validation

## Architecture

```text
Source Bag (recipe)
    ↓ compiler.compile()
Compiled Bag (components expanded, ^pointers resolved)
    ↓ compiler.render()
Output (HTML, Markdown, XML, ...)
```

With `BagAppBase`, data changes trigger automatic updates via the `BindingManager` subscription map.

## Documentation

See the [docs/](docs/) directory for full documentation.

## License

Apache License 2.0 — Copyright 2025 Softwell S.r.l.
