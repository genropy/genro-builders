# genro-builders

Builder system for genro-bag — grammar, validation, compilation.

Provides `BuilderBag`, `BagBuilderBase`, `BagCompilerBase` and concrete
builders (HTML, Markdown, XSD) for creating structured Bag hierarchies
with domain-specific validation.

## Installation

```bash
pip install genro-builders
```

## Quick start

```python
from genro_builders import BuilderBag
from genro_builders.builders import HtmlBuilder

html = BuilderBag(builder=HtmlBuilder)
html.body().div(id='main').p(value='Hello')
```
