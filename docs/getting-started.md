# Getting Started

Build structured output with genro-builders in 5 minutes.

## Install

```bash
pip install genro-builders
```

This also installs [genro-bag](https://github.com/genropy/genro-bag) as a dependency.

## Create an HTML page

```python
from genro_builders.builders import HtmlBuilder

builder = HtmlBuilder()
body = builder.source.body()
body.h1('Welcome')
body.p('This is a paragraph.')

builder.build()
print(builder.output)
```

Output:

```html
<body><h1>Welcome</h1><p>This is a paragraph.</p></body>
```

## Nesting elements

Methods return the created node, so you can nest by chaining or by assigning:

```python
from genro_builders.builders import HtmlBuilder

builder = HtmlBuilder()
body = builder.source.body()
div = body.div(id='main')
div.p('Inside the div')
div.p('Another paragraph')
```

## Attributes

Pass keyword arguments to set HTML attributes:

```python
from genro_builders.builders import HtmlBuilder

builder = HtmlBuilder()
body = builder.source.body()
body.a('Click here', href='https://example.com', target='_blank')
body.img(src='logo.png', alt='Logo')
```

## Markdown output

```python
from genro_builders.builders import MarkdownBuilder

builder = MarkdownBuilder()
builder.source.h1('My Document')
builder.source.p('A paragraph of text.')
builder.source.h2('Section')
builder.source.code('print("hello")', lang='python')

builder.build()
print(builder.output)
```

## Custom builders

Define your own grammar with `@element`:

```python
from genro_builders import BagBuilderBase
from genro_builders.builders import element

class ConfigBuilder(BagBuilderBase):
    @element(sub_tags='setting')
    def section(self): ...

    @element(sub_tags='')
    def setting(self): ...

builder = ConfigBuilder()
db = builder.source.section(node_label='database')
db.setting('localhost', node_label='host')
db.setting(5432, node_label='port')
```

## The `main()` / `store()` pattern

Instead of populating the source manually, you can subclass a builder
and define `main()` (entry point) and `store()` (data population):

```python
from genro_builders.builders import MarkdownBuilder

class MyDoc(MarkdownBuilder):
    def store(self, data):
        data['title'] = 'Monthly Report'
        data['author'] = 'Giovanni'

    def main(self, source):
        source.h1(value='^title')
        source.p(value='^author')
        self.sections(source)

    def sections(self, source):
        source.h2('Summary')
        source.p('...')

doc = MyDoc()
doc.build()
print(doc.output)
```

`store()` is called before `main()`. Both are optional — you can use
either, both, or neither (populating the source manually).

## Reactive data binding

Builders support `^pointer` syntax for reactive data binding. When data
changes, the output updates automatically:

```python
from genro_builders.builders import HtmlBuilder

builder = HtmlBuilder()
builder.data['title'] = 'Hello'
builder.data['text'] = 'World'
builder.source.h1(value='^title')
builder.source.p(value='^text')
builder.build()
print(builder.output)

# Change data — output updates automatically
builder.data['title'] = 'Updated'
print(builder.output)
```

## Node identification

Assign a unique `node_id` to any element for direct access:

```python
from genro_builders.builders import HtmlBuilder

class MyPage(HtmlBuilder):
    def main(self, source):
        source.div(node_id='header').h1('Title')
        source.div(node_id='content').p('Body text')

page = MyPage()
page.build()

header = page.node_by_id('header')   # O(1) lookup
```

Duplicate `node_id` values raise `ValueError`.

---

**Next:** [Quickstart](builders/quickstart.md) — Deep dive into builder grammar and validation
