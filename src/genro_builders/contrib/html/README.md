# HtmlBuilder

W3C HTML5 builder with 112 elements and sub_tags validation.

## Install

```bash
pip install genro-builders
```

## Quick start

```python
from genro_builders.contrib.html import HtmlBuilder


class HelloPage(HtmlBuilder):
    def main(self, root):
        body = root.body()
        body.div(class_="card").p("Hello, world!")


page = HelloPage()
page.create()
print(page.render())
```

## Runtime data binding (pull-based)

The builder owns its datastore, `page.data`, which is flat; `setup`
seeds it:

```python
from genro_builders.contrib.html import HtmlBuilder


class Page(HtmlBuilder):
    def setup(self, data):
        data.set_item("title", "Hello")

    def main(self, root):
        root.body().h1("^title")


page = Page()
page.create()               # setup seeds the data, then main builds
print(page.render())
# ...<h1>Hello</h1>...

page.data.set_item("title", "Updated")
print(page.render())
# ...<h1>Updated</h1>...
```

Re-render is the whole reactivity model here: change the data, render
again. Fine-grained reactivity is a separate engine, still under design —
see the `RX` area of the contract.

## Examples

See [examples/](examples/). Each example is a folder with one page
(`<name>.py`), its rendered output, and a `readme.md`. They are grouped
by what the page needs:

- **no_data/** — pages that are pure structure, no pointers, no data.
- **with_data/** — pages that bind to data via pointers (`^`/`=`,
  datapath, presentation with `mask`/`_wdg`).
- **with_logic/** — data-elements (`dataSetter`/`dataFormula`/
  `dataController`). All three compute at `create()`, once, in document
  order: the datastore is complete before the render starts.

Run an example from its folder: `python <name>.py`. The test suite runs
them all (`tests/test_examples.py`).

## Documentation

Full documentation: [docs/grammars/html.md](../../../../docs/grammars/html.md)
