# genro-builders

Builder system for [genro-bag](https://github.com/genropy/genro-bag) —
domain-specific grammars, rendering, and runtime data binding via
pointers, built on top of bag data structures.

## Installation

```bash
pip install genro-builders
```

## Quick start

A page is a builder: subclass the dialect and implement `main`.

```python
from genro_builders.contrib.html import HtmlBuilder


class HelloPage(HtmlBuilder):
    def main(self, root):
        body = root.body()
        body.h1("Hello World")
        body.p("My first page with genro-builders.")


page = HelloPage()
page.create()
print(page.render(pretty=True))
```

The lifecycle is two-phase, both on the builder:

- **`create()`** runs `setup(self.data)` (seed the data), then the
  user-defined `main(self.source)` that populates the source Bag
  through the dialect's grammar API, then the first calculation of
  the data-elements.
- **`render(mode=None, target=None, **opts)`** drives the universal walk
  on the source and produces the dialect's output. Default `mode` comes
  from the dialect; default `target` returns the string. It composes two
  steps you can also call on their own: `materialize(mode)` walks and
  keeps the result in `materialized[mode]`, `finalize` delivers it.

Rendering does not validate. `validate_source()` reports the nodes whose
minimum child cardinality is unmet — `(fullpath, [missing tags])` per
node, empty when complete — when the author asks for it.

## Dialects (contrib)

The package ships with reference dialects, each as a `<Dialect>Builder`
grammar:

- **HTML5** — `genro_builders.contrib.html.HtmlBuilder`
  (HTML5 grammar with CSS kwargs)
- **SVG** — `genro_builders.contrib.svg.SvgBuilder`
- **CSS** — `genro_builders.contrib.css.CssBuilder`
- **XSD** — `genro_builders.xml` (codegen: an XSD schema becomes a
  `<Dialect>Builder` you commit and import)

Mixed-dialect documents are supported via sub-builders: a grammar
element marked `_meta['subbuilder']` switches the active dialect from
that node down, and the render walk picks the right renderer per node.
HTML hosts SVG with `body.svg(...)`; SVG hosts HTML with
`svg.html(...)`, wrapped in `<foreignObject>` automatically.

```python
from genro_builders.contrib.html import HtmlBuilder


class Badge(HtmlBuilder):
    def main(self, root):
        body = root.body()
        svg = body.svg(viewBox="0 0 200 80", width=200, height=80)
        svg.rect(x=0, y=0, width=200, height=80, fill="#2c3e50")


page = Badge()
page.create()
print(page.render())
```

## Architecture (one-paragraph map)

A **builder** declares the grammar of a dialect (decorators
`@element`, `@abstract`; the three data-elements `dataSetter` /
`dataFormula` / `dataController` are plain `@element` marked as
data) and is also the document: it owns `name`, `source`,
`create()`/`render()`, and exposes its renderers as `renderer_<mode>`
properties. A **handler** (`BuilderHandler`) is the data source: it
mounts ONE builder (`add_builder`) on one FLAT datastore — absolute
paths with no leading segment — and tracks who reads what
(`pointer_map`). It does not render. A
**renderer** is responsible for one mode: the universal walk produces
fragments via dialect-specific `rendered_item`, then `finalize` ships
the result to the target.

## Runtime data binding (pull-based)

Attribute values and node text can carry pointers and templates,
resolved at render time:

- `^path` — reactive pointer (read and subscribed)
- `=path` — passive pointer (read only)
- `${name}` — template token; an attribute referenced by a template
  of the same node is a consumed input, never emitted

```python
from genro_builders.builder import BuilderHandler
from genro_builders.contrib.html import HtmlBuilder


class Page(HtmlBuilder):
    def setup(self, data):
        data.set_item("greeting", "Hello")

    def main(self, root):
        root.body().h1("^greeting")


page = Page()
handler = BuilderHandler()
handler.add_builder(page)      # mounts the page and creates it
print(page.render())
# ...<h1>Hello</h1>...

# Mutate the data and re-render: pull-based, no auto-render.
page.data.set_item("greeting", "Ciao")
print(page.render())
# ...<h1>Ciao</h1>...
```

Re-render is the whole reactivity model here: change the data, render
again. Fine-grained reactivity is a separate engine, still under design —
see the `RX` area of the contract.

The companion API on each source node:

- `node.abs_datapath(path)` — turn a relative path into an absolute
  one in the datastore
- `node.get_relative_data(path)` / `node.set_relative_data(path,
  value)` — read/write the datastore relative to the node
- `node.SET / GET / PUT / FIRE` — the reactive macros over the same
  two entry points

## Render target

```python
page = HelloPage()
page.create()

# Return a string (default)
text = page.render()

# Write to a path
page.render(target="out.html")

# Push to a file-like or invoke a callable
import io
page.render(target=io.StringIO())
page.render(target=print)

# Register a default target (per mode), then render to it
page.set_render_target("out.html")
page.render()
```

## Examples

Runnable tutorials under
[`src/genro_builders/contrib/<dialect>/examples/`](src/genro_builders/contrib/),
grouped by scenario:

- HTML — `no_data/` (grammar, styling, sub-builders, validation,
  render modes), `with_data/` (pointers, datapath, presentation),
  `with_logic/` (data-elements), `reactive/` (live sections)
- SVG — `01_introduction`, `badge_sheet`, `bar_chart`, and more
- CSS — `01_introduction`

Each example ships a runnable `.py`, a `readme.md`, and the rendered
output. The test suite runs them all (`tests/test_examples.py`).

## Documentation

- [Getting Started](docs/getting-started.md) — first page in 5 minutes
- [Builders overview](docs/builders/overview.md) — builder/handler/renderer split
- [Decorators](docs/builders/decorators.md) — `@element`, `@abstract`, sub-builders, data-elements
- [Common patterns](docs/builders/patterns.md) — `._` chaining, `node_by_id`, render targets
- Per-grammar references: [HTML](docs/grammars/html.md), [SVG](docs/grammars/svg.md), [CSS](docs/grammars/css.md), [XSD](docs/grammars/xsd.md)
- Architectural contract and roadmap: [`roadmap/`](roadmap/)

## Downstream

genro-builders is a generic engine: the grammars, the renderers, and the
reactive data binding know nothing about who consumes them. The source carries
no reference to any downstream layer — this is the one place that names them.
Known consumers in the Genro ecosystem:

- **[genro-ws-web](https://github.com/genropy/genro-ws-web)** — WebSocket-driven
  reactive SPA framework (the production widget kit and the push transport live
  here)
- **[genro-office](https://github.com/genropy/genro-office)** — Office document
  generation (Word and Excel builders)
- **[genro-print](https://github.com/genropy/genro-print)** — print and PDF
  generation system
- **[genro-textual](https://github.com/genropy/genro-textual)** — Textual UI
  framework for Bag-driven applications
- **[genro-scriba](https://github.com/genropy/genro-scriba)** — infrastructure
  configuration file generator (Traefik, Docker Compose, and more)

## License

Apache License 2.0 — Copyright 2025 Softwell S.r.l.
