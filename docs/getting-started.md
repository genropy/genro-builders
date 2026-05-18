# Getting started

**Version**: 0.1.0
**Last Updated**: 2026-05-14
**Status**: 🔴 DA REVISIONARE — Documento non ancora approvato.

Build a first page in five minutes.

## Install

```bash
pip install genro-builders
```

## A first HTML page

Define a handler subclass, implement `main(self, root)`, run the
three-phase lifecycle.

```python
from genro_builders.contrib.html import HtmlBuilderHandler


class HelloPage(HtmlBuilderHandler):
    def main(self, root):
        body = root.body()
        body.h1("Hello, world")
        body.p("This is genro-builders.")


page = HelloPage()
page.create()
print(page.render())
```

Output (single line, default mode):

```html
<body><h1>Hello, world</h1><p>This is genro-builders.</p></body>
```

For indented output:

```python
print(page.render(pretty=True))
```

## What just happened

- `HelloPage()` instantiates the handler. The handler owns a builder
  (`HtmlBuilder`), a source bag, and a renderer.
- `page.create()` calls `self.main(self.source)`. You populate the
  source bag using the dialect's fluent API.
- `page.render()` walks the source bag and emits markup.

See [Builders overview](builders/overview.md) for the full lifecycle.

## SVG and CSS

Same pattern, different grammar:

```python
from genro_builders.contrib.svg import SvgBuilderHandler

class Chart(SvgBuilderHandler):
    def main(self, root):
        svg = root.svg(viewBox="0 0 100 100")
        svg.rect(x=10, y=10, width=80, height=80, fill="red")

c = Chart(); c.create()
print(c.render())
```

```python
from genro_builders.contrib.css import CssBuilderHandler

class Theme(CssBuilderHandler):
    def main(self, root):
        sheet = root.stylesheet()
        sheet.rule(color="red", padding="10px")\
             .selector(_class="card")

t = Theme(); t.create()
print(t.render())
```

## Next steps

- [Builders overview](builders/overview.md) — the conceptual model.
- [Common patterns](builders/patterns.md) — `._` chaining,
  `node_by_id`, render targets.
- Per-grammar references: [HTML](grammars/html.md),
  [SVG](grammars/svg.md), [CSS](grammars/css.md).
