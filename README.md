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
print(builder.render())
```

### The manager pattern — `store()` and `main()`

A builder is a machine. To define *what* to build, use a `BuilderManager`:

```python
from genro_builders.builders import HtmlBuilder
from genro_builders.manager import BuilderManager

class HtmlManager(BuilderManager):
    def __init__(self):
        self.page = self.set_builder('page', HtmlBuilder)

    def render(self):
        return self.page.render()

class MyPage(HtmlManager):
    def __init__(self):
        super().__init__()
        self.setup()       # store → main
        self.build()       # source → built

    def store(self, data):
        data['title'] = 'Hello, world!'

    def main(self, source):
        body = source.body()
        body.h1(value='^title')
        self.footer(source)

    def footer(self, source):
        source.footer().p('© 2026')

page = MyPage()
print(page.render())
```

## Features

- **Domain-specific grammars** — Define elements, validation rules, and components via decorators (`@element`, `@abstract`, `@component`)
- **Named slots** — Components can declare insertion points (`slots=['left', 'right']`) for user content injection
- **Built-in builders** — HTML5, Markdown, XSD (schema-driven XML)
- **Reactive pipeline** — Build source, resolve `^pointer` bindings, subscribe for reactivity. Data changes trigger automatic re-render
- **Multi-builder coordination** — `BuilderManager` coordinates multiple builders with a shared data store
- **Renderers and compilers** — `@renderer` for serialized output (HTML, Markdown), `@compiler` for live objects (widgets, workbooks)
- **Node identification** — `node_id` attribute for O(1) lookup via `node_by_id()`
- **Validation** — `sub_tags` cardinality, `parent_tags` constraints, typed attribute validation

## Architecture

A builder is a machine that materializes a source Bag into a built Bag.
A `BuilderManager` mixin orchestrates population and lifecycle:

```text
setup()           →  build()         →  subscribe()     →  render() / compile()
store + main         source → built     activate            output
(populate)           (materialize)      reactivity
```

- **`setup()`** — on manager: calls `store(data)` then `main(source)`
- **`build()`** — materialize: expand components, resolve `^pointer` bindings
- **`subscribe()`** — optional: activate reactive bindings (data changes trigger re-render)
- **`render()`** — produce serialized output via `BagRendererBase`
- **`compile()`** — produce live objects via `BagCompilerBase`

## Documentation

See the [docs/](docs/) directory for full documentation.

## License

Apache License 2.0 — Copyright 2025 Softwell S.r.l.
