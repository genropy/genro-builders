# genro-builders

Builder system for [genro-bag](https://github.com/genropy/genro-bag) — grammar, validation, reactive data binding, and computed data infrastructure.

## Installation

```bash
pip install genro-builders
```

## Quick start

```python
from genro_builders.contrib.html import HtmlBuilder

builder = HtmlBuilder()
body = builder.source.body()
body.div(id='main').p('Hello, world!')

builder.build()
print(builder.render())
```

### The manager pattern — `store()` and `main()`

A builder is a machine. To define *what* to build, use a `BuilderManager`:

```python
from genro_builders.contrib.html import HtmlBuilder
from genro_builders.manager import BuilderManager

class HtmlManager(BuilderManager):
    def __init__(self):
        self.page = self.set_builder('page', HtmlBuilder)

    def render(self):
        return self.page.render()

class MyPage(HtmlManager):
    def __init__(self):
        super().__init__()
        self.setup()       # store -> main
        self.build()       # source -> built

    def store(self, data):
        data['title'] = 'Hello, world!'

    def main(self, source):
        body = source.body()
        body.h1(value='^title')
        self.footer(source)

    def footer(self, source):
        source.footer().p('(c) 2026')

page = MyPage()
print(page.render())
```

## Features

- **Domain-specific grammars** — Define elements, validation rules, and components via decorators (`@element`, `@abstract`, `@component`)
- **Data infrastructure** — `@data_element` decorator for `data_setter`, `data_formula`, and `data_controller` — write, compute, and act on the reactive data store directly from the source Bag
- **Reactive formulas** — `data_formula` with `^pointer` dependencies re-executes automatically when sources change, in topological order (dependencies first, cycles detected)
- **Computed attributes** — Callable attributes with `^pointer` defaults are resolved just-in-time during render/compile
- **Debounce and periodic** — `_delay` for debounced formula re-execution, `_interval` for periodic polling
- **Output suspension** — `suspend_output()` / `resume_output()` to batch data changes and trigger a single render
- **Pointer formali** — The built Bag retains `^pointer` strings; resolution happens just-in-time during render/compile, not during build
- **Named slots** — Components can declare insertion points (`slots=['left', 'right']`) for user content injection
- **Contributed builders** — HTML5, Markdown, XSD in `genro_builders.contrib` (optional, not loaded unless imported)
- **Multi-builder coordination** — `BuilderManager` coordinates multiple builders with a shared data store
- **Renderers and compilers** — `@renderer` for serialized output (HTML, Markdown), `@compiler` for live objects (widgets, workbooks)
- **Node identification** — `node_id` attribute for O(1) lookup via `node_by_id()`
- **Validation** — `sub_tags` cardinality, `parent_tags` constraints, typed attribute validation via `Annotated`

## Architecture

A builder is a machine that materializes a source Bag into a built Bag.
A `BuilderManager` mixin orchestrates population and lifecycle:

```text
setup()           ->  build()              ->  subscribe()     ->  render() / compile()
store + main          two-pass walk:           activate            output
(populate)            1. data elements         reactivity
                      2. normal elements
```

- **`setup()`** — on manager: calls `store(data)` then `main(source)`
- **`build()`** — two-pass materialize:
  - **Pass 1**: process data elements (data_setter writes values, data_formula computes, data_controller executes side effects)
  - **Pass 2**: materialize normal elements and components into the built Bag, register `^pointer` bindings
  - After both passes: topological sort of formulas, fire `_onBuilt` hooks
- **`subscribe()`** — optional: activate reactive bindings. Data changes trigger formula re-execution and automatic re-render. Starts `_interval` timers.
- **`render()`** — produce serialized output via `BagRendererBase` (just-in-time `^pointer` resolution)
- **`compile()`** — produce live objects via `BagCompilerBase` (just-in-time `^pointer` resolution)

## Data infrastructure

Data elements let you define computed and reactive data directly in the source Bag:

```python
from genro_builders.contrib.html import HtmlBuilder

builder = HtmlBuilder()
s = builder.source

# Static data
s.data_setter('greeting', value='Hello')

# Computed data (re-executes when ^greeting changes)
s.data_formula('message', func=lambda greeting: f'{greeting}, World!',
               greeting='^greeting')

# Controller (side effect, no output path)
s.data_controller(func=lambda message: print(f'Message: {message}'),
                   message='^message')

# UI bound to computed data
s.body().h1(value='^message')

builder.build()
builder.subscribe()
print(builder.output)
# <body><h1>Hello, World!</h1></body>

# Change source data -> formula re-executes -> re-render
builder.data['greeting'] = 'Ciao'
print(builder.output)
# <body><h1>Ciao, World!</h1></body>
```

### Debounce and periodic execution

```python
# Re-execute at most once every 500ms (debounce)
s.data_formula('search_results', func=do_search,
               query='^search.query', _delay=0.5)

# Re-execute every 10 seconds (polling)
s.data_formula('clock', func=lambda: time.strftime('%H:%M:%S'),
               _interval=10.0)
```

### Output suspension

```python
builder.suspend_output()     # pause rendering
builder.data['a'] = 1
builder.data['b'] = 2
builder.data['c'] = 3        # no render triggered yet
builder.resume_output()       # single render with all 3 changes
```

## Documentation

See the [docs/](docs/) directory for full documentation:

- [Getting Started](docs/getting-started.md) — Build your first page in 5 minutes
- [Custom Builders](docs/builders/custom-builders.md) — Define your own grammar
- [Reactive Data](docs/builders/reactive-data.md) — Data elements, formulas, reactivity
- [Architecture](docs/builders/architecture.md) — Build pipeline, pointer formali, formula registry

## License

Apache License 2.0 — Copyright 2025 Softwell S.r.l.
