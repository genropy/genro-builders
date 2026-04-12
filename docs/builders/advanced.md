# Advanced Patterns

This guide covers advanced builder patterns for complex use cases.

## Builder Inheritance

### Extending Existing Builders

```{doctest}
>>> from genro_builders import BuilderBag
>>> from genro_builders.builder import BagBuilderBase, element

>>> class BaseUIBuilder(BagBuilderBase):
...     """Base builder with common UI elements."""
...
...     @element()
...     def container(self): ...
...
...     @element()
...     def text(self): ...

>>> class ExtendedUIBuilder(BaseUIBuilder):
...     """Extended builder with additional elements."""
...
...     @element()
...     def button(self): ...
...
...     @element(sub_tags='option')
...     def select(self): ...
...
...     @element()
...     def option(self): ...

>>> bag = BuilderBag(builder=ExtendedUIBuilder)
>>> cont = bag.container()  # From parent
>>> cont.text('Label')  # From parent
BagNode : ... at ...
>>> cont.button('Submit')  # From child
BagNode : ... at ...
>>> sel = cont.select()  # From child
>>> sel.option('A')  # doctest: +ELLIPSIS
BagNode : ... at ...
```

## SchemaBuilder: Programmatic Schema Creation

`SchemaBuilder` allows you to define schemas programmatically instead of using decorators. This is useful for:

- Dynamic schema generation
- Schemas loaded from external sources
- Reusable schema definitions shared across builders

### Basic Usage

```{doctest}
>>> from genro_builders import BuilderBag
>>> from genro_builders.builder import SchemaBuilder

>>> schema = BuilderBag(builder=SchemaBuilder)

>>> # Define elements with the item() method
>>> schema.item('document', sub_tags='chapter')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> schema.item('chapter', sub_tags='section,paragraph')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> schema.item('section', sub_tags='paragraph')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> schema.item('paragraph')  # Leaf element (no children)  # doctest: +ELLIPSIS
BagNode : ... at ...
```

### The item() Method

```python
schema.item(
    name: str,              # Element name (or '@name' for abstract)
    sub_tags: str = '',     # Valid child tags with cardinality
    inherits_from: str = None,  # Abstract element to inherit from
)
```

### Defining Abstract Elements

Use `@` prefix for abstract elements:

```{doctest}
>>> from genro_builders import BuilderBag
>>> from genro_builders.builder import SchemaBuilder

>>> schema = BuilderBag(builder=SchemaBuilder)

>>> # Define abstract (content category)
>>> schema.item('@inline', sub_tags='span,strong,em')  # doctest: +ELLIPSIS
BagNode : ... at ...

>>> # Concrete element inherits from abstract
>>> schema.item('p', inherits_from='@inline')  # doctest: +ELLIPSIS
BagNode : ... at ...

>>> schema.item('span')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> schema.item('strong')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> schema.item('em')  # doctest: +ELLIPSIS
BagNode : ... at ...
```

### Compiling to File

Save the schema for reuse:

```python
# Save to MessagePack (binary, compact)
schema.builder.save_schema('my_schema.msgpack')
```

### Using Compiled Schema

Load the schema in a custom builder:

```python
from genro_builders import BuilderBag
from genro_builders.builder import BagBuilderBase

# Method 1: Class attribute
class MyBuilder(BagBuilderBase):
    _schema_path = 'my_schema.msgpack'

# Method 2: Constructor parameter
bag = BuilderBag(builder=BagBuilderBase, builder_schema_path='my_schema.msgpack')
```

### Complete Example: Config Schema

```{doctest}
>>> from genro_builders import BuilderBag
>>> from genro_builders.builder import SchemaBuilder, BagBuilderBase

>>> # Create schema programmatically
>>> schema = BuilderBag(builder=SchemaBuilder)
>>> schema.item('config', sub_tags='database,cache[:1],logging[:1]')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> schema.item('database')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> schema.item('cache')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> schema.item('logging')  # doctest: +ELLIPSIS
BagNode : ... at ...

>>> # Use the schema directly (without saving to file)
>>> class ConfigBuilder(BagBuilderBase):
...     pass

>>> # The schema would normally be loaded from file
>>> # For this example, we show the pattern
```

### When to Use SchemaBuilder vs @element

| Approach | Use When |
|----------|----------|
| `@element` decorator | Schema is static, defined in code |
| `SchemaBuilder` | Schema is dynamic, generated at runtime |
| `SchemaBuilder` + file | Schema is shared across multiple builders |
| XSD → SchemaBuilder | Schema comes from external XSD file |

## Loading Schema from File

Builders can load schema from a pre-compiled MessagePack file using `_schema_path`:

```python
from genro_builders import BuilderBag
from genro_builders.builder import BagBuilderBase

class MyBuilder(BagBuilderBase):
    _schema_path = 'path/to/schema.msgpack'  # Load at class definition

# Or pass at instantiation
bag = BuilderBag(builder=MyBuilder, builder_schema_path='custom_schema.msgpack')
```

## Custom Validation

For custom validation logic, see [Validation](validation.md).

## Performance Tips

### 1. Use Batch Operations

```python
# Instead of validating each step:
for data in large_dataset:
    parent.item(data)

# Validate once at the end:
errors = builder.validate()
```

## Real-World Example: Config Builder

```{doctest}
>>> from genro_builders import BuilderBag
>>> from genro_builders.builder import BagBuilderBase, element

>>> class ConfigBuilder(BagBuilderBase):
...     """Builder for application configuration."""
...
...     @element(sub_tags='database,cache[:1],logging[:1],features')
...     def config(self): ...
...
...     @element()
...     def database(self): ...
...
...     @element()
...     def cache(self): ...
...
...     @element()
...     def logging(self): ...
...
...     @element()
...     def features(self): ...

>>> bag = BuilderBag(builder=ConfigBuilder)
>>> config = bag.config(env='development')
>>> config.database(host='db.local', port=5433)  # doctest: +ELLIPSIS
<genro_bag.bag.Bag object at ...>
>>> config.cache(enabled=True, ttl=7200)  # doctest: +ELLIPSIS
<genro_bag.bag.Bag object at ...>
>>> config.logging(level='DEBUG')  # doctest: +ELLIPSIS
<genro_bag.bag.Bag object at ...>
>>> config.features('dark_mode,beta_ui')  # doctest: +ELLIPSIS
BagNode : ... at ...

>>> # Validate structure
>>> errors = bag.builder.validate()
>>> errors
[]

>>> # Access config values
>>> config['database_0?host']
'db.local'
>>> config['database_0?port']
5433
```

## Reactive Formulas

Data formulas let you define computed values that re-execute automatically
when their `^pointer` dependencies change. See [Reactive Data](reactive-data.md)
for the full guide.

### Formula Dependency Chains

When formulas depend on each other, they execute in topological order:

```python
from genro_builders.contrib.html import HtmlBuilder

builder = HtmlBuilder()
s = builder.source

s.data_setter('base_price', value=100)
s.data_setter('discount', value=0.1)
s.data_setter('tax_rate', value=0.22)

# Executes first: depends on base_price and discount
s.data_formula('net_price',
    func=lambda base_price, discount: base_price * (1 - discount),
    base_price='^base_price',
    discount='^discount',
)

# Executes second: depends on net_price (computed above)
s.data_formula('total',
    func=lambda net_price, tax_rate: net_price * (1 + tax_rate),
    net_price='^net_price',
    tax_rate='^tax_rate',
)

s.body().p(value='^total')

builder.build()
builder.subscribe()
print(builder.output)

# Change base_price -> net_price recalculates -> total recalculates -> re-render
builder.data['base_price'] = 200
print(builder.output)
```

### Computed Attributes

Callable attributes are resolved via 2-pass evaluation on the node.
In pass 1 all `^pointer` attributes are resolved to values. In pass 2,
callables are called with matching resolved attributes as kwargs:

```python
# Callable that uses other resolved attributes
s.body().div(
    price="^item.price",
    qty=3,
    total=lambda price, qty: price * qty,
)

# Callable with ^pointer defaults (resolved from data store)
s.body().div(
    style=lambda bg='^theme.bg', fg='^theme.fg': f'background:{bg};color:{fg}',
)
```

## Output Suspension

When making multiple data changes, use `suspend_output()` / `resume_output()`
to avoid redundant re-renders:

```python
builder.build()
builder.subscribe()

builder.suspend_output()
builder.data['a'] = 1
builder.data['b'] = 2
builder.data['c'] = 3        # formulas re-execute, but no render
builder.resume_output()       # single render with all changes applied
```

This is useful for initialization patterns where many data values are
set at once, or for batch updates from external sources.

## Debounce and Periodic Execution

### Debounce with `_delay`

Prevent rapid re-execution with a debounce window:

```python
s.data_formula('search_results',
    func=lambda query: api_search(query),
    query='^search.query',
    _delay=0.5,  # wait 500ms after last change
)
```

### Periodic with `_interval`

Re-execute at regular intervals after `subscribe()`:

```python
import time

s.data_formula('clock',
    func=lambda: time.strftime('%H:%M:%S'),
    _interval=1.0,  # every second
)
```

Interval timers start on `subscribe()` and stop on rebuild or clear.
