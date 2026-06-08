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
        body.div(class_="card").p("Hello, world!")


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

See [examples/](examples/). Each example is a folder with one page
(`<name>.py`), its rendered output, and a `readme.md`. They are grouped
by what the page needs:

- **no_data/** — pages that are pure structure, no pointers, no handler:
  `00_hello_world`, `01_inline_styling`, `02_nested_structure`,
  `03_subbuilders`, `04_methods`, `05_struct_method`, `06_render_modes`,
  `07_validation`.
- **with_data/** — pages that bind to data via pointers (`^`/`=`,
  data-elements). _(work in progress)_

Run an example from its folder: `python <name>.py`.

## Documentation

Full documentation: [docs/grammars/html.md](../../../../docs/grammars/html.md)
