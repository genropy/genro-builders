# HtmlBuilder

W3C HTML5 builder with 112 elements and sub_tags validation.

## Install

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

## Reactive data binding

```python
builder = HtmlBuilder()
builder.data['title'] = 'Hello'
builder.source.body().h1(value='^title')

builder.build()
builder.subscribe()
print(builder.output)

builder.data['title'] = 'Updated'
print(builder.output)
```

## Examples

See [examples/](examples/) for complete working examples:

- **html_page_example.py** — Shopping list and contacts table
- **simple_page.py** — Minimal HTML page
- **contact_list.py** — Declarative contact list with builder pattern
- **weather_dashboard.py** — Live dashboard with resolver-backed data

## Documentation

Full documentation: [docs/builders/html-builder.md](../../../../docs/builders/html-builder.md)
