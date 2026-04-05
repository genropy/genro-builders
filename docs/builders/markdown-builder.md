# MarkdownBuilder

The `MarkdownBuilder` provides elements for building Markdown documents programmatically. The `MarkdownRenderer` walks the built Bag and renders each node using `@renderer` handlers (declarative templates or logic methods).

## Basic Usage

```{doctest}
>>> from genro_builders import BuilderBag
>>> from genro_builders.contrib.markdown import MarkdownBuilder

>>> doc = BuilderBag(builder=MarkdownBuilder)
>>> doc.h1("My Document")  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> doc.p("This is a paragraph.")  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> md = doc.builder._compile()
>>> print(md)
# My Document
<BLANKLINE>
This is a paragraph.
```

## Common Patterns

### Headings

```{doctest}
>>> from genro_builders import BuilderBag
>>> from genro_builders.contrib.markdown import MarkdownBuilder

>>> doc = BuilderBag(builder=MarkdownBuilder)
>>> doc.h1("Title")  # doctest: +ELLIPSIS
BagNode : ...
>>> doc.h2("Subtitle")  # doctest: +ELLIPSIS
BagNode : ...
>>> doc.h3("Section")  # doctest: +ELLIPSIS
BagNode : ...
>>> print(doc.builder._compile())
# Title
<BLANKLINE>
## Subtitle
<BLANKLINE>
### Section
```

### Code Blocks

```{doctest}
>>> from genro_builders import BuilderBag
>>> from genro_builders.contrib.markdown import MarkdownBuilder

>>> doc = BuilderBag(builder=MarkdownBuilder)
>>> doc.code("print('hello')", lang="python")  # doctest: +ELLIPSIS
BagNode : ...
>>> print(doc.builder._compile())
```python
print('hello')
```
```

### Tables

```{doctest}
>>> from genro_builders import BuilderBag
>>> from genro_builders.contrib.markdown import MarkdownBuilder

>>> doc = BuilderBag(builder=MarkdownBuilder)
>>> table = doc.table()
>>> header = table.tr()
>>> header.th("Name")  # doctest: +ELLIPSIS
BagNode : ...
>>> header.th("Value")  # doctest: +ELLIPSIS
BagNode : ...
>>> row = table.tr()
>>> row.td("foo")  # doctest: +ELLIPSIS
BagNode : ...
>>> row.td("bar")  # doctest: +ELLIPSIS
BagNode : ...
>>> print(doc.builder._compile())
| Name | Value |
| --- | --- |
| foo | bar |
```

### Lists

#### Unordered Lists

```{doctest}
>>> from genro_builders import BuilderBag
>>> from genro_builders.contrib.markdown import MarkdownBuilder

>>> doc = BuilderBag(builder=MarkdownBuilder)
>>> ul = doc.ul()
>>> ul.li("First item")  # doctest: +ELLIPSIS
BagNode : ...
>>> ul.li("Second item")  # doctest: +ELLIPSIS
BagNode : ...
>>> ul.li("Third item")  # doctest: +ELLIPSIS
BagNode : ...
>>> print(doc.builder._compile())
- First item
- Second item
- Third item
```

#### Ordered Lists

```{doctest}
>>> from genro_builders import BuilderBag
>>> from genro_builders.contrib.markdown import MarkdownBuilder

>>> doc = BuilderBag(builder=MarkdownBuilder)
>>> ol = doc.ol()
>>> ol.li("First step")  # doctest: +ELLIPSIS
BagNode : ...
>>> ol.li("Second step")  # doctest: +ELLIPSIS
BagNode : ...
>>> ol.li("Third step")  # doctest: +ELLIPSIS
BagNode : ...
>>> print(doc.builder._compile())
1. First step
2. Second step
3. Third step
```

#### Custom List Markers

Use the `idx` parameter for custom markers:

```{doctest}
>>> from genro_builders import BuilderBag
>>> from genro_builders.contrib.markdown import MarkdownBuilder

>>> doc = BuilderBag(builder=MarkdownBuilder)
>>> ol = doc.ol()
>>> ol.li("Item A", idx="a)")  # doctest: +ELLIPSIS
BagNode : ...
>>> ol.li("Item B", idx="b)")  # doctest: +ELLIPSIS
BagNode : ...
>>> print(doc.builder._compile())
a) Item A
b) Item B
```

### Inline Elements

```{doctest}
>>> from genro_builders import BuilderBag
>>> from genro_builders.contrib.markdown import MarkdownBuilder

>>> doc = BuilderBag(builder=MarkdownBuilder)
>>> doc.bold("important")  # doctest: +ELLIPSIS
BagNode : ...
>>> doc.italic("emphasis")  # doctest: +ELLIPSIS
BagNode : ...
>>> doc.link("Click here", href="https://example.com")  # doctest: +ELLIPSIS
BagNode : ...
>>> doc.inlinecode("code")  # doctest: +ELLIPSIS
BagNode : ...
>>> print(doc.builder._compile())
**important**
<BLANKLINE>
*emphasis*
<BLANKLINE>
[Click here](https://example.com)
<BLANKLINE>
`code`
```

### Blockquotes

```{doctest}
>>> from genro_builders import BuilderBag
>>> from genro_builders.contrib.markdown import MarkdownBuilder

>>> doc = BuilderBag(builder=MarkdownBuilder)
>>> doc.blockquote("This is a quote.")  # doctest: +ELLIPSIS
BagNode : ...
>>> print(doc.builder._compile())
> This is a quote.
```

### Images

```{doctest}
>>> from genro_builders import BuilderBag
>>> from genro_builders.contrib.markdown import MarkdownBuilder

>>> doc = BuilderBag(builder=MarkdownBuilder)
>>> doc.img(src="image.png", alt="My Image")  # doctest: +ELLIPSIS
BagNode : ...
>>> print(doc.builder._compile())
![My Image](image.png)
```

## Compile to File

The `_compile()` method can optionally write to a file:

```python
from genro_builders import BuilderBag
from genro_builders.contrib.markdown import MarkdownBuilder

doc = BuilderBag(builder=MarkdownBuilder)
doc.h1("My Document")
doc.p("Content here.")

# Write to file
doc.builder._compile(destination="output.md")
```

## Complete Example

```{doctest}
>>> from genro_builders import BuilderBag
>>> from genro_builders.contrib.markdown import MarkdownBuilder

>>> doc = BuilderBag(builder=MarkdownBuilder)
>>> doc.h1("Project README")  # doctest: +ELLIPSIS
BagNode : ...
>>> doc.p("A brief description of the project.")  # doctest: +ELLIPSIS
BagNode : ...

>>> doc.h2("Installation")  # doctest: +ELLIPSIS
BagNode : ...
>>> doc.code("pip install my-project", lang="bash")  # doctest: +ELLIPSIS
BagNode : ...

>>> doc.h2("Features")  # doctest: +ELLIPSIS
BagNode : ...
>>> ul = doc.ul()
>>> ul.li("Feature 1")  # doctest: +ELLIPSIS
BagNode : ...
>>> ul.li("Feature 2")  # doctest: +ELLIPSIS
BagNode : ...

>>> md = doc.builder._compile()
>>> "# Project README" in md
True
>>> "pip install my-project" in md
True
```

## Schema Reference

```{include} markdown-builder-schema.md
```
