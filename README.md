# genro-builders

Builder system for [genro-bag](https://github.com/genropy/genro-bag) —
domain-specific grammars, rendering, and runtime data binding via
pointers, built on top of bag data structures.

## Installation

```bash
pip install genro-builders
```

## Quick start

```python
from genro_builders.contrib.html import HtmlBuilderHandler


class HelloPage(HtmlBuilderHandler):
    def main(self, root):
        body = root.body()
        body.h1("Hello World")
        body.p("My first page with genro-builders.")


page = HelloPage()
page.create()
print(page.render())
```

The lifecycle is two-phase:

- **`create()`** invokes the user-defined `main(self, source)` that
  populates the source Bag through the dialect's grammar API.
- **`render(mode=None, target=None, **opts)`** drives the universal
  walk on the source and produces the dialect's output. Default
  `mode` comes from the handler or the builder; default `target`
  returns the string.

## Dialects (contrib)

The package ships with four reference dialects, each as a
`<Dialect>BuilderHandler` pre-bound to its grammar:

- **HTML5** — `genro_builders.contrib.html.HtmlBuilderHandler`
  (HTML5 grammar with CSS kwargs and Genro macros)
- **SVG** — `genro_builders.contrib.svg.SvgBuilderHandler`
- **CSS** — `genro_builders.contrib.css.CssBuilderHandler`
- **XSD** — `genro_builders.contrib.xsd` (codegen, schema-only)

Mixed-dialect documents are supported via sub-builder polymorphism:
attach a different dialect under a node and the render walk picks
the right renderer per builder. The standard SVG-hosting-HTML case
wraps the HTML subtree in `<foreignObject xmlns="...">` automatically.

```python
from genro_builders.contrib.svg import SvgBuilderHandler


class Badge(SvgBuilderHandler):
    def main(self, root):
        svg = root.svg(viewBox="0 0 200 80", width=200, height=80)
        svg.rect(x=0, y=0, width=200, height=80, fill="#2c3e50")
        # HTML subtree wrapped in <foreignObject> by the renderer.
        fo = svg.html(x=20, y=20, width=160, height=40)
        fo.div("Mixed content", style="color: white")


page = Badge()
page.create()
print(page.render())
```

## Architecture (one-paragraph map)

A **builder** declares the grammar of a dialect (decorators
`@element`, `@abstract`, `@subbuilder`, `@data`, `@data_formula`,
`@data_controller`) and exposes its renderers as `renderer_<mode>`
properties. A **handler** drives
the lifecycle for a single builder instance: it owns the source bag,
the data bag, the pointer map and the render target registry. A
**renderer** is responsible for one mode: the universal walk on
`RendererBase.render` produces fragments via dialect-specific
`rendered_item(node, item, runtime_attrs, **opts)`, then `finalize`
ships the result to the target.

## Runtime data binding (pull-based)

Attribute values and node text can carry pointers and templates that
are resolved at render time, on the node itself:

- `^path` — lazy pointer (re-evaluated on every read)
- `=path` — eager pointer (resolved once, value cached)
- `${name}` — template token inside a string attribute or node value

```python
class Page(HtmlBuilderHandler):
    def main(self, root):
        # The value '^greeting' is resolved at render time.
        root.body().h1("^greeting")


page = Page()
page.create()
page.data.set_item("greeting", "Hello")
print(page.render())
# <body><h1>Hello</h1></body>

# Mutate the data bag and re-render: pull-based, no auto-render yet.
page.data.set_item("greeting", "Ciao")
print(page.render())
# <body><h1>Ciao</h1></body>
```

Push reactivity (`subscribe`/auto-render on data change) is on the
roadmap (`RX`); the pull-based slice above is the current contract.

The companion API on each node:

- `node.runtime_values()` — return `(value, attrs)` after pointer
  and template resolution
- `node.abs_datapath(path)` — turn a relative path into an absolute
  one in the data bag
- `node.get_relative_data(path, autocreate=False, default=None)` —
  read from the data bag
- `node.set_relative_data(path, value, attributes=None, fired=False,
  reason=None)` — write to the data bag
- `node.fire_event(path, value=True, ...)` — shortcut for
  `set_relative_data(..., fired=True)`

## Render target

```python
page = HelloPage()
page.create()

# Return a string (default)
text = page.render()

# Write to a path (parent dirs created)
page.render(target="out.html")

# Push to a file-like
import io
buf = io.StringIO()
page.render(target=buf)

# Invoke a callable
page.render(target=print)

# Register a default target per mode
page.set_render_target("html", "out.html", default=True)
page.render()
```

## Examples

Runnable tutorials under
[`src/genro_builders/contrib/<dialect>/examples/`](src/genro_builders/contrib/):

- HTML — `01_introduction`, `02_inline_styling`, `03_subbuilders`
- SVG — `01_introduction` ... `06_*`, plus `badge_sheet`
- CSS — `01_introduction`

Each example ships three views: a runnable `.py`, an annotated
notebook `.ipynb`, and the resulting `.html` output.

## Documentation

- [Getting Started](docs/getting-started.md) — first page in 5 minutes
- [Builders overview](docs/builders/overview.md) — handler/builder/renderer split
- [Decorators](docs/builders/decorators.md) — `@element`, `@abstract`, `@subbuilder`, `@data`, `@data_formula`, `@data_controller`
- [Common patterns](docs/builders/patterns.md) — `._` chaining, `node_by_id`, render targets
- Per-grammar references: [HTML](docs/grammars/html.md), [SVG](docs/grammars/svg.md), [CSS](docs/grammars/css.md)
- Architectural contract and roadmap: [`roadmap/`](roadmap/)

## License

Apache License 2.0 — Copyright 2025 Softwell S.r.l.
