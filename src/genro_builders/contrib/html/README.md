# HtmlBuilder

W3C HTML5 builder with 112 elements and sub_tags validation.

## Install

```bash
pip install genro-builders
```

## Quick start

```python
from genro_builders.contrib.html import HtmlBuilderHandler


class HelloPage(HtmlBuilderHandler):
    def main(self, root):
        body = root.body()
        body.div(_class="card").p("Hello, world!")


page = HelloPage()
page.create()
print(page.render())
```

## Runtime data binding (pull-based)

```python
class Page(HtmlBuilderHandler):
    def main(self, root):
        root.body().h1("^title")


page = Page()
page.create()
page.data.set_item("title", "Hello")
print(page.render())
# <body><h1>Hello</h1></body>

page.data.set_item("title", "Updated")
print(page.render())
# <body><h1>Updated</h1></body>
```

Push reactivity (`subscribe`/auto-render) is on the roadmap (`RX`);
the pull-based slice above is the current contract.

## Examples

See [examples/](examples/) — three tutorials, each shipped as
`.py` + `.ipynb` + rendered `.html`:

- **01_introduction** — minimal HtmlBuilderHandler with `main` /
  `create` / `render`.
- **02_inline_styling** — CSS kwargs, Genro macros (`rounded`,
  `gradient`, ...), `style_*` escapes.
- **03_subbuilders** — host SVG inside HTML and vice versa
  (`<foreignObject>` wrapping).

## Documentation

Full documentation: [docs/grammars/html.md](../../../../docs/grammars/html.md)
