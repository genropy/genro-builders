# Getting started

**Last Updated**: 2026-07-27
**Status**: 🟢 APPROVATO — allineato al contratto v0.9.0.

Build a first page in five minutes.

## Install

```bash
pip install genro-builders
```

## A first HTML page

A page is a builder: subclass the dialect, implement `main(self,
root)`, run the two-phase lifecycle (`create()` then `render()`).

```python
from genro_builders.contrib.html import HtmlBuilder


class HelloPage(HtmlBuilder):
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

- `HelloPage()` instantiates the builder: grammar plus document
  (`source` bag, render lifecycle).
- `page.create()` calls `setup(self.data)` then `main(self.source)`.
  You populate the source bag using the dialect's fluent API.
- `page.render()` walks the source bag and emits markup. Renderers
  are `renderer_<mode>` properties on the builder class.

See [Builders overview](builders/overview.md) for the full lifecycle,
including the data-bound scenario (`BuilderHandler`).

## SVG and CSS

Same pattern, different grammar:

```python
from genro_builders.contrib.svg import SvgBuilder

class Chart(SvgBuilder):
    def main(self, root):
        svg = root.svg(viewBox="0 0 100 100")
        svg.rect(x=10, y=10, width=80, height=80, fill="red")

c = Chart(); c.create()
print(c.render())
```

```python
from genro_builders.contrib.css import CssBuilder

class Theme(CssBuilder):
    def main(self, root):
        sheet = root.stylesheet()
        card = sheet.selector(class_="card")
        card.rule(color="red", padding="10px")

t = Theme(); t.create()
print(t.render())
```

## Next steps

- [Builders overview](builders/overview.md) — the conceptual model.
- [Common patterns](builders/patterns.md) — `._` chaining,
  `node_by_id`, render targets.
- Per-grammar references: [HTML](grammars/html.md),
  [SVG](grammars/svg.md), [CSS](grammars/css.md).
