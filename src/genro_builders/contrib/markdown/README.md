# MarkdownBuilder

Markdown document builder with headings, paragraphs, lists, tables, code blocks,
and inline formatting.

## Install

```bash
pip install genro-builders
```

## Quick start

```python
from genro_builders.contrib.markdown import MarkdownBuilder

builder = MarkdownBuilder()
builder.source.h1('My Document')
builder.source.p('A paragraph of text.')
builder.source.h2('Code Example')
builder.source.code('print("hello")', lang='python')

builder.build()
print(builder.render())
```

## Examples

See [examples/](examples/) for complete working examples:

- **markdown_report.py** — Document with headings, tables, and code blocks

## Documentation

Full documentation: [docs/builders/markdown-builder.md](../../../../docs/builders/markdown-builder.md)
