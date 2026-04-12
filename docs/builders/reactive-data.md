# Reactive Data Infrastructure

genro-builders provides a complete reactive data infrastructure that lets you
define computed values, side effects, and reactive bindings directly in the
source Bag via **data elements**.

## Overview

Data elements are declared with the `@data_element` decorator. Three built-in
data elements are available on every builder:

| Element | Purpose | Has output path? |
|---------|---------|:----------------:|
| `data_setter` | Write a static value to the data Bag | Yes |
| `data_formula` | Compute a value from `^pointer` dependencies | Yes |
| `data_controller` | Execute a side effect when dependencies change | No |

Data elements are **transparent**: they do not appear in the built Bag. They are
processed during Pass 1 of the build walk, before normal elements are materialized.

## data_setter

Writes a value at a path in the data Bag:

```python
builder = HtmlBuilder()
s = builder.source

s.data_setter('user.name', value='Giovanni')
s.data_setter('user.role', value='admin')

s.body().p(value='^user.name')

builder.build()
print(builder.output)
# <body><p>Giovanni</p></body>
```

If the value is a `dict`, it is automatically converted to a `Bag`.

## data_formula

Computes a value by calling a function with resolved `^pointer` arguments.
The result is written at the given path in the data Bag:

```python
builder = HtmlBuilder()
s = builder.source

s.data_setter('price', value=100)
s.data_setter('tax_rate', value=0.22)

s.data_formula('total',
    func=lambda price, tax_rate: price * (1 + tax_rate),
    price='^price',
    tax_rate='^tax_rate',
)

s.body().p(value='^total')

builder.build()
builder.subscribe()
print(builder.output)
# <body><p>122.0</p></body>

# Change a dependency -> formula re-executes -> re-render
builder.data['price'] = 200
print(builder.output)
# <body><p>244.0</p></body>
```

### Formula dependencies and topological sort

When multiple formulas depend on each other, they are automatically sorted
in topological order before execution. If formula A writes to a path that
formula B reads via `^pointer`, A always executes before B.

```python
s.data_setter('base', value=10)
s.data_formula('doubled', func=lambda base: base * 2, base='^base')
s.data_formula('quadrupled', func=lambda doubled: doubled * 2, doubled='^doubled')
# Execution order: base -> doubled -> quadrupled
```

Circular dependencies are detected at build time and raise `ValueError`.

### Debounce with `_delay`

When a formula has `_delay`, it debounces: only the last trigger within the
delay window actually executes. Useful for search-as-you-type patterns:

```python
s.data_formula('search_results',
    func=lambda query: api_search(query),
    query='^search.query',
    _delay=0.5,   # seconds
)
```

If `^search.query` changes 10 times in 400ms, the formula executes only once
(500ms after the last change).

### Periodic execution with `_interval`

When a formula has `_interval`, it re-executes periodically after `subscribe()`:

```python
import time

s.data_formula('clock',
    func=lambda: time.strftime('%H:%M:%S'),
    _interval=1.0,   # every second
)
```

The interval timer starts when `subscribe()` is called and stops when the
builder is rebuilt or the built Bag is cleared.

## data_controller

Executes a function for side effects only. It has no output path — the result
is discarded. Useful for logging, API calls, or triggering external actions:

```python
s.data_controller(
    func=lambda total: print(f'Order total: {total}'),
    total='^total',
)
```

Controllers support `_delay` and `_interval` just like formulas.

## `_node` injection

If a formula or controller function accepts a `_node` parameter (or `**kwargs`),
the source BagNode is injected automatically. This gives access to the full
node context:

```python
def my_formula(price, _node=None):
    # _node is the source BagNode for this data_formula
    return price * 1.22

s.data_formula('total', func=my_formula, price='^price')
```

## `_onBuilt` hook

Data elements can include an `_onBuilt` callable that fires once after
the entire build is complete (after topological sort, before `subscribe()`):

```python
s.data_controller(
    func=lambda: None,
    _onBuilt=lambda builder: print(f'Build complete: {len(builder.built)} nodes'),
)
```

## Output suspension

When making multiple data changes at once, use `suspend_output()` /
`resume_output()` to avoid redundant re-renders:

```python
builder.subscribe()

builder.suspend_output()     # pause
builder.data['a'] = 1
builder.data['b'] = 2
builder.data['c'] = 3        # formulas re-execute, but no render
builder.resume_output()       # single render with all changes applied
```

## Computed attributes

Any callable attribute on a built node whose parameter defaults are
`^pointer` strings is treated as a **computed attribute**. During
render/compile, the callable is invoked with resolved values:

```python
s.body().div(
    style=lambda bg='^theme.bg', fg='^theme.fg': f'background:{bg};color:{fg}',
)
```

When `^theme.bg` or `^theme.fg` change, the `style` attribute is re-computed
on the next render.

## Pointer formali

The built Bag retains `^pointer` strings verbatim. Resolution happens
just-in-time during render/compile via `node.runtime_value` and
`node.runtime_attrs` (which call `evaluate_on_node(data)` internally). This
design means:

- The built Bag is a stable structural representation.
- Multiple renderers/compilers can resolve the same built Bag against
  different data snapshots.
- Data changes don't require re-building — only re-rendering.

## Two-pass build

The `build()` method processes the source Bag in two passes:

1. **Pass 1 — Data elements**: all `data_setter`, `data_formula`, and
   `data_controller` nodes are processed first. They write to the data Bag,
   register in the formula registry, and collect `_onBuilt` hooks.

2. **Pass 2 — Normal elements**: elements and components are materialized
   into the built Bag. `^pointer` bindings are registered (but not resolved).

After both passes:
- Formulas are sorted in topological order.
- `_onBuilt` hooks are fired.

This guarantees that data is available before normal elements try to read it
via `^pointer` bindings.

## Custom data elements

You can define your own data elements with `@data_element`:

```python
from genro_builders.builders import BagBuilderBase, data_element, element

class MyBuilder(BagBuilderBase):
    @element()
    def item(self): ...

    @data_element()
    def data_timer(self, path, func=None, interval=1.0, **kwargs):
        """Custom data element with default interval."""
        return path, dict(func=func, _interval=interval, **kwargs)
```

The handler body receives the raw arguments and must return
`(path, attrs_dict)`. The `path` is the data path (or `None` for
controller-like elements), and `attrs_dict` contains the attributes
to store on the source node.
