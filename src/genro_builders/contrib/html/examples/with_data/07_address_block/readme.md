# 07 — Address block

A **component** is a grammar element with a body: calling it puts a
node *named after the component* in the source; at render time the
body builds the real structure into a throw-away root, and what it
built is rendered in the node's place. The source stays a clean
recipe — the expansion is ephemeral, it never enters the tree.

## A reusable block in a mixin

```python
class CommonComponents:

    @component
    def address_block(self, root, company=None, street=None,
                      city=None, zip_code=None):
        card = root.div(class_="address")
        card.strong(company)
        card.div(street)
        card.div("${zip_code} ${city}", zip_code=zip_code, city=city)


class CustomPage(HtmlBuilder, CommonComponents):
    ...
```

The mixin enters the grammar like any element mixin; the body stays
callable on the class. The body receives a fresh root and MUST build
exactly **one** tree into it (one root element — the `div.address`);
a forest raises.

## Calling it with explicit params

```python
body.address_block(
    company="^sender.company", street="^sender.street",
    city="^sender.city", zip_code="^sender.zip",
)
```

The call's attributes saturate the body's signature. Plain values
arrive as they are; a **reactive pointer passes through AS a pointer**
(absolutized — `^html:sender.city`): the body stamps it on the nodes
it builds, and the value resolves at the final node's render, exactly
like a hand-written pointer. That is what keeps the ADDRESS alive on
the element (the `data-value-pointer` write-back hook in the reactive
render). Consequence: the body builds structure with the kwargs, it
never computes on their values — composing two data into one string is
the template's job (`${zip_code} ${city}`, inputs consumed), not an
f-string's. The same component renders the customer block from literal
params — the call site decides the data.

## Why this example exists

It exercises the single-component path of the render walk: named node
in the source, ephemeral expansion, tree-not-forest, params by
signature (contract area `CMP`, design in
`roadmap/component-design.md`). The iterate form (`iterate='^path'`)
is the next step of the same design.

Run it from this folder:

```bash
python address_block.py
```
