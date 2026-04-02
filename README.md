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

### Subclass pattern with `main()` and `store()`

```python
from genro_builders.builders import HtmlBuilder

class MyPage(HtmlBuilder):
    def store(self, data):
        data['title'] = 'Hello, world!'

    def main(self, source):
        body = source.body()
        body.h1(value='^title')
        self.footer(source)

    def footer(self, source):
        source.footer().p('© 2026')

page = MyPage()
page.build()
print(page.output)
```

## Features

- **Domain-specific grammars** — Define elements, validation rules, and components via decorators (`@element`, `@abstract`, `@component`)
- **Named slots** — Components can declare insertion points (`slots=['left', 'right']`) for user content injection
- **Built-in builders** — HTML5, Markdown, XSD (schema-driven XML)
- **Reactive pipeline** — Build source, resolve `^pointer` bindings, render output. Data changes trigger automatic re-render
- **Multi-builder coordination** — `BuilderManager` coordinates multiple builders with a shared data store
- **Renderers and compilers** — `@renderer` for serialized output (HTML, Markdown), `@compiler` for live objects (widgets, workbooks)
- **Node identification** — `node_id` attribute for O(1) lookup via `node_by_id()`
- **Validation** — `sub_tags` cardinality, `parent_tags` constraints, typed attribute validation

## Architecture

A builder owns the full pipeline:

```text
store(data)   →  main(source)  →  build()  →  render() / compile()  →  output
                      │               │                │
                 @element,      components        string (render)
                 @component     expanded,         or live objects
                 as nodes       ^pointers         (compile)
                                resolved
```

- **`store(data)`** — optional: populate the data Bag
- **`main(source)`** — entry point: build the element tree
- **`build()`** — materialize: expand components, resolve `^pointer` bindings
- **`render()`** — produce serialized output via `BagRendererBase`
- **`compile()`** — produce live objects via `BagCompilerBase`

Data changes after build trigger automatic updates via `BindingManager`.

## Documentation

See the [docs/](docs/) directory for full documentation.

## License

Apache License 2.0 — Copyright 2025 Softwell S.r.l.
