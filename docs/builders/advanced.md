# Advanced Patterns

This guide covers advanced builder patterns for complex use cases.

## Builder Inheritance

### Extending Existing Builders

```{doctest}
>>> from genro_builders import BuilderBag
>>> from genro_builders.builders import BagBuilderBase, element

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
>>> from genro_builders.builders import SchemaBuilder

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
>>> from genro_builders.builders import SchemaBuilder

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
schema.builder._compile('my_schema.msgpack')
```

### Using Compiled Schema

Load the schema in a custom builder:

```python
from genro_builders import BuilderBag
from genro_builders.builders import BagBuilderBase

# Method 1: Class attribute
class MyBuilder(BagBuilderBase):
    _schema_path = 'my_schema.msgpack'

# Method 2: Constructor parameter
bag = BuilderBag(builder=BagBuilderBase, builder_schema_path='my_schema.msgpack')
```

### Complete Example: Config Schema

```{doctest}
>>> from genro_builders import BuilderBag
>>> from genro_builders.builders import SchemaBuilder, BagBuilderBase

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
from genro_builders.builders import BagBuilderBase

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
errors = builder._check()
```

## Real-World Example: Config Builder

```{doctest}
>>> from genro_builders import BuilderBag
>>> from genro_builders.builders import BagBuilderBase, element

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
>>> errors = bag.builder._check()
>>> errors
[]

>>> # Access config values
>>> config['database_0?host']
'db.local'
>>> config['database_0?port']
5433
```
