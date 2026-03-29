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

builder.compile()
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

builder.compile()
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

## Reactive data binding

Builders support `^pointer` syntax for reactive data binding. When data
changes, the output updates automatically:

```python
from genro_builders.builders import HtmlBuilder
from genro_builders.compiler import BagCompilerBase, compile_handler

class MyCompiler(BagCompilerBase):
    @compile_handler
    def h1(self, node, ctx):
        return f"<h1>{ctx['node_value']}</h1>"

    @compile_handler
    def p(self, node, ctx):
        return f"<p>{ctx['node_value']}</p>"

    def render(self, compiled_bag):
        parts = list(self._walk_compile(compiled_bag))
        return '\n'.join(p for p in parts if p)

HtmlBuilder._compiler_class = MyCompiler

builder = HtmlBuilder()
builder.data['title'] = 'Hello'
builder.data['text'] = 'World'
builder.source.h1(value='^title')
builder.source.p(value='^text')
builder.compile()
print(builder.output)
# <h1>Hello</h1>
# <p>World</p>

# Change data — output updates automatically
builder.data['title'] = 'Updated'
print(builder.output)
# <h1>Updated</h1>
# <p>World</p>
```

---

**Next:** [Quickstart](builders/quickstart.md) — Deep dive into builder grammar and validation
