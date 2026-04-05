# Validation

Builders support two types of validation:

1. **Structure Validation** - Which children are allowed under which parents
2. **Attribute Validation** - Type checking, enums, required fields

## Structure Validation

### Defining Valid Children

Use the `sub_tags` parameter in `@element` to specify allowed child tags:

```{doctest}
>>> from genro_builders import BuilderBag
>>> from genro_builders.builders import BagBuilderBase, element

>>> class DocumentBuilder(BagBuilderBase):
...     @element(sub_tags='chapter')
...     def book(self): ...
...
...     @element(sub_tags='section,paragraph')
...     def chapter(self): ...
...
...     @element(sub_tags='paragraph')
...     def section(self): ...
...
...     @element()
...     def paragraph(self): ...

>>> bag = BuilderBag(builder=DocumentBuilder)
>>> book = bag.book()
>>> ch1 = book.chapter()
>>> ch1.paragraph('Introduction')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> sec = ch1.section()
>>> sec.paragraph('Detail')  # doctest: +ELLIPSIS
BagNode : ... at ...
```

### Wildcard: Accept Any Children

Use `sub_tags='*'` to create container elements that accept any child without validation:

```{doctest}
>>> from genro_builders import BuilderBag
>>> from genro_builders.builders import BagBuilderBase, element

>>> class FlexibleBuilder(BagBuilderBase):
...     @element(sub_tags='*')  # Accepts ANY children
...     def container(self): ...
...
...     @element()
...     def span(self): ...
...
...     @element()
...     def div(self): ...
...
...     @element()
...     def custom(self): ...

>>> bag = BuilderBag(builder=FlexibleBuilder)
>>> container = bag.container()
>>> container.span('text')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> container.div()  # doctest: +ELLIPSIS
<genro_bag.bag.Bag object at ...>
>>> container.custom('anything')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> len(container.value)
3
```

**Key points:**

- `sub_tags='*'` disables child validation entirely
- Useful for generic container elements
- `validate()` will not report errors for unknown children
- Different from `sub_tags=''` which means **no children allowed** (leaf element)

| Syntax | Meaning |
|--------|---------|
| `sub_tags='*'` | Accept any children (no validation) |
| `sub_tags=''` | Leaf element (no children allowed) |
| `sub_tags='a,b'` | Only `a` and `b` allowed |

### Cardinality Constraints

Specify minimum and maximum occurrences with bracket syntax:

| Syntax | Meaning |
|--------|---------|
| `tag` | Any number (0..N) |
| `tag[1]` | Exactly 1 |
| `tag[3]` | Exactly 3 |
| `tag[0:]` | 0 or more (same as `tag`) |
| `tag[1:]` | At least 1 |
| `tag[:3]` | 0 to 3 |
| `tag[2:5]` | Between 2 and 5 |

> **Note:** `tag[]` (empty brackets) is **not valid** syntax and raises `ValueError`.
> Use `tag` for 0..N or `tag[0:]` explicitly.

```{doctest}
>>> from genro_builders import BuilderBag
>>> from genro_builders.builders import BagBuilderBase, element

>>> class PageBuilder(BagBuilderBase):
...     @element(sub_tags='header,content,footer[:1]')
...     def page(self):
...         """Page must have exactly 1 header, 1 content, at most 1 footer."""
...         ...
...
...     @element()
...     def header(self): ...
...
...     @element()
...     def content(self): ...
...
...     @element()
...     def footer(self): ...
```

### The validate() Method

Use `validate()` to validate structure after building. It walks the bag and returns
a list of dicts (with keys ``path``, ``tag``, ``reasons``) for every invalid node:

```{doctest}
>>> from genro_builders import BuilderBag
>>> from genro_builders.builders import BagBuilderBase, element

>>> class ListBuilder(BagBuilderBase):
...     @element(sub_tags='item[1:]')  # At least 1 item required
...     def list(self): ...
...
...     @element()
...     def item(self): ...

>>> bag = BuilderBag(builder=ListBuilder)
>>> lst = bag.list()

>>> # Empty list - validation fails
>>> errors = bag.builder.validate()
>>> len(errors) > 0
True

>>> # Add items - now valid
>>> lst.item('First')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> lst.item('Second')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> errors = bag.builder.validate()
>>> errors
[]
```

### Invalid Children Detection

```{doctest}
>>> from genro_builders import BuilderBag
>>> from genro_builders.builders import BagBuilderBase, element

>>> class StrictBuilder(BagBuilderBase):
...     @element(sub_tags='allowed')
...     def container(self): ...
...
...     @element()
...     def allowed(self): ...
...
...     @element()
...     def forbidden(self): ...

>>> bag = BuilderBag(builder=StrictBuilder)
>>> cont = bag.container()
>>> cont.allowed('OK')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> cont.forbidden('Oops')  # Structurally added, but invalid
BagNode : ... at ...

>>> errors = bag.builder.validate()
>>> len(errors) > 0
True
```

### Restricting Valid Parents (parent_tags)

Use `parent_tags` to specify where an element can be placed. This is the inverse of `sub_tags`:

- `sub_tags`: "What children can I have?"
- `parent_tags`: "What parents can I be inside?"

```{doctest}
>>> from genro_builders import BuilderBag
>>> from genro_builders.builders import BagBuilderBase, element

>>> class HtmlBuilder(BagBuilderBase):
...     @element(sub_tags='li')
...     def ul(self): ...
...
...     @element(sub_tags='li')
...     def ol(self): ...
...
...     @element(parent_tags='ul,ol')  # li MUST be inside ul or ol
...     def li(self): ...
...
...     @element(sub_tags='li')  # Allows li as child (sub_tags)
...     def div(self): ...

>>> bag = BuilderBag(builder=HtmlBuilder)

>>> # Valid: li inside ul
>>> ul = bag.ul()
>>> ul.li('Item 1')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> bag.builder.validate()
[]

>>> # Invalid: li inside div (div allows li via sub_tags, but li rejects div via parent_tags)
>>> div = bag.div()
>>> div.li('Invalid item')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> errors = bag.builder.validate()
>>> len(errors) > 0
True
```

**Key points:**

- `parent_tags` is a comma-separated list of allowed parent tags
- Element is added but **marked invalid** if parent doesn't match
- Validation happens at build time, errors collected via `validate()`
- Works with both `@element` and `@component`

### Combining sub_tags and parent_tags

Use both parameters for complete bidirectional validation:

```python
class StrictHtmlBuilder(BagBuilderBase):
    @element(sub_tags='tr')
    def tbody(self): ...

    @element(sub_tags='td', parent_tags='tbody,thead,tfoot')
    def tr(self): ...

    @element(parent_tags='tr')
    def td(self): ...
```

This ensures:
- `tbody` can only contain `tr`
- `tr` can only be inside `tbody`, `thead`, or `tfoot`
- `td` can only be inside `tr`

## Attribute Validation

Attribute validation is handled automatically by the builder. Pass attributes as keyword arguments when calling elements:

```{doctest}
>>> from genro_builders import BuilderBag
>>> from genro_builders.builders import BagBuilderBase, element

>>> class ButtonBuilder(BagBuilderBase):
...     @element()
...     def button(self): ...

>>> bag = BuilderBag(builder=ButtonBuilder)
>>> bag.button('Submit', variant='primary')  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> bag.button('Delete', variant='danger')  # doctest: +ELLIPSIS
BagNode : ... at ...
```

## Combining Structure and Attribute Validation

A complete example with structure constraints:

```{doctest}
>>> from genro_builders import BuilderBag
>>> from genro_builders.builders import BagBuilderBase, element

>>> class TableBuilder(BagBuilderBase):
...     @element(sub_tags='thead[:1],tbody,tfoot[:1]')
...     def table(self): ...
...
...     @element(sub_tags='tr')
...     def thead(self): ...
...
...     @element(sub_tags='tr[1:]')  # At least 1 row
...     def tbody(self): ...
...
...     @element(sub_tags='tr')
...     def tfoot(self): ...
...
...     @element(sub_tags='th,td')
...     def tr(self): ...
...
...     @element()
...     def th(self): ...
...
...     @element()
...     def td(self): ...

>>> bag = BuilderBag(builder=TableBuilder)
>>> table = bag.table()
>>> tbody = table.tbody()
>>> row = tbody.tr()
>>> row.td('Cell 1', colspan=2)  # doctest: +ELLIPSIS
BagNode : ... at ...
>>> row.td('Cell 2')  # doctest: +ELLIPSIS
BagNode : ... at ...
```

## Best Practices

### 1. Define Constraints Early

Document your schema constraints clearly:

```python
class ConfigBuilder(BagBuilderBase):
    """Builder for application config.

    Structure:
        config
        ├── database     # Required, exactly one
        ├── cache[:1]    # Optional, at most one
        └── logging[:1]  # Optional, at most one
    """
    @element(sub_tags='database,cache[:1],logging[:1]')
    def config(self): ...
```

### 2. Validate After Building

Always validate complete structures before use:

```python
bag = BuilderBag(builder=MyBuilder)
# ... build the structure ...

errors = bag.builder.validate()
if errors:
    for err in errors:
        print(f"ERROR at {err['path']}: {err['reasons']}")
    raise ValueError("Invalid structure")
```

### 3. Use sub_tags for Self-Documentation

The `sub_tags` parameter serves as documentation and enables validation:

```python
@element(sub_tags='input,button,textarea')
def form(self):
    """Form element that accepts inputs, buttons, and textareas."""
    ...
```
