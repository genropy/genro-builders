# Reactive Data Infrastructure

genro-builders provides a pull-based reactive data infrastructure. Computed
values are `FormulaResolver` instances installed on the data store — they
compute on-demand when read, with no push cascade.

## Overview

Two built-in data elements are available on every builder:

| Element | Purpose | Mechanism |
|---------|---------|-----------|
| `data_setter` | Write a static value to the data Bag | One-shot at build time |
| `data_formula` | Install a computed value resolver | FormulaResolver on data node |

Both are **transparent**: they do not appear in the built Bag. They are
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
print(builder.render())
# <body><p>Giovanni</p></body>
```

If the value is a `dict`, it is automatically converted to a `Bag`.

## data_formula

Installs a `FormulaResolver` on the data store node. The resolver computes
the value on-demand by calling `func` with resolved `^pointer` arguments:

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
print(builder.render())
# <body><p>122.0</p></body>

# Change a dependency -> re-render shows fresh value (pull)
builder.data['price'] = 200
print(builder.render())
# <body><p>244.0</p></body>
```

### Formula cascades (pull model)

When formulas depend on each other, the cascade resolves naturally via
demand-driven reads. Reading `data['quadrupled']` triggers its resolver,
which reads `data['doubled']`, which triggers its resolver, which reads
`data['base']`. No topological sort needed.

```python
s.data_setter('base', value=10)
s.data_formula('doubled', func=lambda base: base * 2, base='^base')
s.data_formula('quadrupled', func=lambda doubled: doubled * 2, doubled='^doubled')

builder.build()
print(builder.data['quadrupled'])  # 40
```

### Active cache with `_cache_time`

For periodic background refresh, use `_cache_time=-N` (negative = active cache,
N seconds between refreshes). Requires an async context:

```python
import time

s.data_formula('clock',
    func=lambda: time.strftime('%H:%M:%S'),
    _cache_time=-1,   # refresh every second
)
```

With active cache:
- `read_only=False`: result stored in node, triggers data change events
- Background timer refreshes the value periodically
- Reading the value returns the cached result (fast)
- Data subscribers are notified on each refresh

## Side effects

Side effects (logging, file writes, API calls) are handled via
`data.subscribe()` on the data store, not via the builder:

```python
class MyApp(ReactiveManager):
    def __init__(self):
        self.page = self.set_builder('page', HtmlBuilder)
        self.run(subscribe=True)
        # Subscribe for side effects
        self.reactive_store.subscribe(
            'logger',
            any=lambda pathlist=None, **kw: print(f'Changed: {pathlist}'),
        )
```

## `_onBuilt` hook

Data elements can include an `_onBuilt` callable that fires once after
the build is complete:

```python
s.data_formula('total',
    func=lambda price: price * 1.22,
    price='^price',
    _onBuilt=lambda builder: print(f'Build complete'),
)
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

## Explicit render (no auto-render)

In the pull model, the builder does NOT auto-render on data changes.
Call `render()` explicitly when you want output. This makes batching natural:

```python
builder.build()
builder.subscribe()

# Multiple changes, no render yet
builder.data['a'] = 1
builder.data['b'] = 2
builder.data['c'] = 3

# Single render with all changes applied
output = builder.render()
```

## Pointer formali

The built Bag retains `^pointer` strings verbatim. Resolution happens
just-in-time during render/compile via `node.runtime_value` and
`node.runtime_attrs` (which call `evaluate_on_node()` internally). This
design means:

- The built Bag is a stable structural representation.
- Multiple renderers/compilers can resolve the same built Bag against
  different data snapshots.
- Data changes don't require re-building — only re-rendering.

## Two-pass build

The `build()` method processes the source Bag in two passes:

1. **Pass 1 — Data infrastructure**: `data_setter` writes static values,
   `data_formula` installs `FormulaResolver` instances on data store nodes.
   Neither leaves a trace in the built Bag.

2. **Pass 2 — Normal elements**: elements and components are materialized
   into the built Bag. `^pointer` bindings stay formal.

After both passes, formula resolvers with `_on_built=True` are warmed up
(initial read triggers computation), and `_onBuilt` hooks are fired.
