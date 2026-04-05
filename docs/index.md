# genro-builders

[![GitHub](https://img.shields.io/badge/GitHub-genro--builders-blue?logo=github)](https://github.com/genropy/genro-builders)

Builder system for [genro-bag](https://github.com/genropy/genro-bag) — grammar, validation, compilation, and reactive data binding.

## What are Builders?

A builder defines a **domain-specific grammar** for creating structured Bag hierarchies. Instead of manually constructing nodes, you call named methods that enforce structure and validation:

```python
from genro_builders.contrib.html import HtmlBuilder

builder = HtmlBuilder()
body = builder.source.body()
div = body.div(id='main')
div.p('Hello, world!')

builder.build()
print(builder.render())
# <body><div id="main"><p>Hello, world!</p></div></body>
```

## Key Concepts

- **BagBuilderBase** — Base class for defining grammars via `@element`, `@abstract`, `@component`, and `@data_element` decorators. A builder is a machine: it materializes a source Bag into a built Bag.
- **BuilderBag** — A Bag extended with builder support. Calling methods like `.div()` or `.p()` creates validated nodes.
- **Data infrastructure** — `data_setter`, `data_formula`, and `data_controller` write, compute, and act on the reactive data store. Formulas re-execute in topological order when dependencies change.
- **Pointer formali** — The built Bag retains `^pointer` strings. Resolution happens just-in-time during render/compile.
- **BagRendererBase** — Transforms a built Bag into serialized output (strings, bytes) via `@renderer` handlers.
- **BagCompilerBase** — Transforms a built Bag into live objects (widgets, workbooks) via `@compiler` handlers.
- **BuilderManager** — Mixin to coordinate one or more builders with a shared reactive data store. Provides `setup()`, `build()`, and `subscribe()`.

## Contributed Builders

Available in `genro_builders.contrib`:

| Builder              | Import                                                        | Output   |
| -------------------- | ------------------------------------------------------------- | -------- |
| **HtmlBuilder**      | `from genro_builders.contrib.html import HtmlBuilder`         | HTML5    |
| **MarkdownBuilder**  | `from genro_builders.contrib.markdown import MarkdownBuilder` | Markdown |
| **SvgBuilder**       | `from genro_builders.contrib.svg import SvgBuilder`           | SVG      |
| **XsdBuilder**       | `from genro_builders.contrib.xsd import XsdBuilder`           | XML      |

## Lifecycle

```text
setup()           →  build()         →  subscribe()     →  render() / compile()
store + main         source → built     activate            output
(populate)           (materialize)      reactivity
```

1. **setup()** — on manager: calls `store(data)` then `main(source)` to populate
2. **build()** — two-pass materialize: data elements first (setter/formula/controller), then normal elements. Topological sort of formula dependencies.
3. **subscribe()** — optional: activate reactive bindings. Data changes trigger formula re-execution and automatic re-render. Enables `_delay` (debounce) and `_interval` (periodic).
4. **render() / compile()** — produce output with just-in-time `^pointer` resolution (pointer formali)

```python
from genro_builders.contrib.html import HtmlBuilder

builder = HtmlBuilder()
builder.data['title'] = 'Hello'
builder.data['text'] = 'World'
builder.source.h1(value='^title')
builder.source.p(value='^text')
builder.build()
builder.subscribe()          # activate reactivity
print(builder.output)

# Data changes trigger automatic re-render
builder.data['title'] = 'Updated'
print(builder.output)
```

---

**Next:** [Getting Started](getting-started.md) — Build your first page in 5 minutes

```{toctree}
:maxdepth: 1
:caption: Start Here
:hidden:

getting-started
```

```{toctree}
:maxdepth: 2
:caption: Builders
:hidden:

builders/README
builders/quickstart
builders/custom-builders
builders/html-builder
builders/markdown-builder
builders/svg-builder
builders/xsd-builder
builders/reactive-data
builders/validation
builders/advanced
builders/examples
builders/faq
builders/architecture
```

```{toctree}
:maxdepth: 1
:caption: Reference
:hidden:

reference/architecture
reference/benchmarks
reference/full-faq
```
