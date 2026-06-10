# 08 — Component store

The second calling form of a component: instead of passing each datum
as a parameter (see `07_address_block`), the caller anchors the
component to a **record** in the datastore. `store` is the component's
data anchor.

## A body made of relative pointers

```python
class CommonComponents:

    @component
    def address_block(self, root, **kwargs):
        card = root.div(**kwargs)
        card.strong("^.company")
        card.div("^.street")
        card.div("${z} ${c}", z="^.zip", c="^.city")
```

The body reads the record through relative pointers (`^.company`),
plus the usual grammar niceties (here a template with consumed inputs
composes "zip city"). The call's other attributes flow in as
``kwargs`` and the author routes them — here onto the card, so the
caller can dress the block (`class_`, `style`, ...) while the root
stays the author's.

## Anchoring at the call site

```python
body.address_block(store="^sender", class_="address")
body.address_block(store="^customer", class_="address compact")
```

The SAME body renders different blocks depending on the record it is
anchored to. `store` is a machinery word: it is consumed (never
reaches the body, never emitted) and it is not resolved to a value —
it is a **path**, stamped as `datapath` on the expansion's throw-away
wrapper, so the body's relative pointers find it through the ordinary
ancestor climb.

## Reactivity shape (design `CMP.7`)

The component node's own `store` pointer registers in the
pointer_map; the expansion's pointers resolve at render but register
nothing. One coarse subscription per component — when the record
changes, the block re-renders.

Run it from this folder:

```bash
python component_store.py
```
