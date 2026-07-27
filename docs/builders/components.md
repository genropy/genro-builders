# Components

A **component** is a reusable piece of grammar: a named element that
carries a body. You declare it once and call it like any other tag; at
render time its body builds a fresh subtree that becomes the node's
content. The body runs **only at render time** — the source tree holds a
single component node until then.

```python
from genro_builders.builder import component
from genro_builders.contrib.html import HtmlBuilder


class CommonComponents:
    @component
    def productCard(self, root, name=None, price=None):
        card = root.div(class_="card")
        card.h3(name)
        card.p(price, class_="price")


class Page(HtmlBuilder, CommonComponents):
    def main(self, root):
        root.body().productCard(name="Widget", price="9.90")
```

`@component` is a **bare decorator** — it takes no arguments. The tag is
the method name, and a same-named plain element is overridden by the
component. The body signature is `def name(self, root, ...)`: `root` is
the fresh subtree to fill.

## Where components live

Group them in a mixin and add the mixin to a builder's bases (or enrich a
single instance with `include_components(*mixins)`). The mixin's
components become part of that builder's grammar, callable on any node.

## The three calling forms

The decorator is always bare; what varies is **how you call** the element.

### 1. Explicit parameters

The call saturates the body's parameters. Values may be literals or
pointers; a reactive pointer (`^...`) **passes through** to the inner
node as a pointer (so it survives for write-back and re-render), it is
not resolved at call time.

```python
@component
def addressBlock(self, root, company=None, street=None, city=None):
    card = root.div(class_="address")
    card.strong(company)
    card.div(street)
    card.div(city)

# call site:
body.addressBlock(company="^sender.company", street="^sender.street",
                  city="^sender.city")          # pointers
body.addressBlock(company="ACME", street="123 Main St", city="Springfield")  # literals
```

To compose two data into one string use a **template**, not an f-string:
a pointer kwarg reaches the body as a pointer, its value exists only at
the final node's render.

```python
card.div("${zip} ${city}", zip="^.zip", city="^.city")
```

### 2. `store` — anchored to a record

`store` is the component's **data anchor**: the same body renders a
different block depending on the record it is anchored to. The body reads
the record through *relative* pointers (`^.field`); the call's other
attributes flow in as `**kwargs` for the author to route.

```python
@component
def addressBlock(self, root, **kwargs):
    card = root.div(**kwargs)
    card.strong("^.company")
    card.div("^.street")
    card.div("${z} ${c}", z="^.zip", c="^.city")

# call site — one body, two records:
body.addressBlock(store="^sender", class_="address")
body.addressBlock(store="^customer", class_="address compact")
```

`store` is a path, not a value: it does not resolve to data, it relocates
the body's relative pointers onto that record.

### 3. `iterate` — one expansion per child

`iterate` expands the body **once per child** of a collection. The body
signature takes `node_label=None`: the renderer passes only the child's
label, and the body anchors its root to that child.

```python
@component
def stateRow(self, root, node_label=None):
    row = root.tr(datapath="." + node_label)
    row.td("^.name")
    row.td("^.capital")

# call site — one source node, one <tr> per child of ^states:
tbody.stateRow(iterate="^states")
```

## Composing components

Components compose fractally: a component body may call other components,
and datapaths compose across the levels. A component may even call
*itself* to walk tree-shaped data, terminating when the data runs out.

## Following the data

A component registers **one** reader — the component node itself — not
one per expanded row: the expansion is ephemeral, it reincarnates at
every render. So the way a block follows its data is rendering the
document again, which re-expands it over the current values. Granular
updates are refounded on a compiled bag emitted by a `livehtml` render
mode — see the `RX` area of the contract.

## Worked examples

Runnable, in the three-view format:
[`src/genro_builders/contrib/html/examples/with_data/`](https://github.com/genropy/genro-builders/tree/main/src/genro_builders/contrib/html/examples/with_data/)

- `07_address_block` — explicit parameters
- `08_component_store` — the `store` anchor
- `09_component_iterate` — `iterate` over a collection
- `10_component_nesting` — components within components
- `11_component_recursion` — self-recursion over tree data

## `@container` — the other reusable citizen

`@container` is the complement to `@component`. Where a component is
*closed* (the caller parameterizes it, the body expands at render time), a
container **generates real source nodes at call time** and is **fillable**
by the caller: the body runs immediately, writes addressable nodes, and
returns a handle (a pane, a zones object) the caller goes on to fill.

```python
from genro_builders.builder import container

class Layout:
    @container
    def panel(self, pane, title=None):
        pane.h3(title)
        return pane.div(class_="panel-body")   # caller fills this

# call site:
body = root.panel(title="Settings")            # real nodes exist now
body.p("...")                                   # caller fills the returned handle
```

Two naming forms:

```python
@container
def widget(self, pane, ...): ...        # dispatch name: 'widget'

@container('alias')
def some_internal_name(self, pane, ...): ...   # dispatch name: 'alias'
```

A container must carry a real body (an empty `...` body raises). The
discriminator between the two citizens is **fillability**: a component is
closed and expands at render time; a container builds now and hands back
something to fill. See the example
[`with_data/13_container_collection`](https://github.com/genropy/genro-builders/tree/main/src/genro_builders/contrib/html/examples/with_data/13_container_collection/).
