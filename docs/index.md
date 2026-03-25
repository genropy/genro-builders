# genro-builders

[![GitHub](https://img.shields.io/badge/GitHub-genro--builders-blue?logo=github)](https://github.com/genropy/genro-builders)

Builder system for [genro-bag](https://github.com/genropy/genro-bag) — grammar, validation, compilation, and reactive data binding.

## What are Builders?

A builder defines a **domain-specific grammar** for creating structured Bag hierarchies. Instead of manually constructing nodes, you call named methods that enforce structure and validation:

```python
from genro_builders import BuilderBag
from genro_builders.builders import HtmlBuilder

html = BuilderBag(builder=HtmlBuilder)
body = html.body()
div = body.div(id='main')
div.p('Hello, world!')

print(html.builder._compile())
# <body><div id="main"><p>Hello, world!</p></div></body>
```

## Key Concepts

- **BuilderBag** — A Bag extended with builder support. Calling methods like `.div()` or `.p()` creates validated nodes.
- **BagBuilderBase** — Abstract base class for defining grammars via `@element`, `@abstract`, and `@component` decorators.
- **BagCompilerBase** — Compiles a source bag (expanding components, resolving `^pointers`) and renders output.
- **BagAppBase** — Reactive application runtime: recipe, compile, bind, render — with automatic updates on data or source changes.

## Built-in Builders

| Builder | Output | Description |
|---------|--------|-------------|
| **HtmlBuilder** | HTML5 | Full W3C HTML5 schema with validation |
| **MarkdownBuilder** | Markdown | Headings, paragraphs, lists, tables, code blocks |
| **XsdBuilder** | XML | Schema-driven XML from XSD files |

## Reactive Pipeline

genro-builders supports a 4-stage reactive pipeline via `BagAppBase`:

1. **Source Bag** — Recipe with builder calls, unexpanded components, `^pointer` strings
2. **Compiled Bag** — Components expanded, `^pointers` resolved against data
3. **Bound Bag** — Subscriptions active, data changes update nodes automatically
4. **Output** — Rendered by the compiler (HTML, Markdown, etc.)

```python
from genro_builders import BagAppBase
from genro_builders.builders import HtmlBuilder

class MyApp(BagAppBase):
    builder_class = HtmlBuilder

    def recipe(self, source):
        source.h1(value='^page.title')
        source.p(value='^content.text')

app = MyApp()
app.data['page.title'] = 'Hello'
app.data['content.text'] = 'World'
app.setup()
print(app.output)
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
builders/html-builder
builders/markdown-builder
builders/xsd-builder
builders/custom-builders
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
