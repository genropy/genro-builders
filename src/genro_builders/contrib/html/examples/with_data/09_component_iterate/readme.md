# 09 — Component iterate

The third calling form of a component: **replication over a
collection**. `iterate` points to a Bag in the datastore; at render
time the body runs once per child — N blocks from ONE source node.
The source stays a clean recipe: it holds the component node with its
`iterate`, never the N expansions.

## The repeating block

```python
class CommonComponents:

    @component
    def stateRow(self, root, node_label=None):
        row = root.tr(datapath="." + node_label)
        row.td("^.name")
        row.td("^.capital")
```

Each round receives ONLY the item's label (`node_label`). The body
anchors its root to that item — `datapath="." + node_label`, relative
to the collection the caller iterated — and reads the item's fields
with relative pointers. Tag and attributes of the row belong to the
component's author, as always.

## Iterating at the call site

```python
tbody.stateRow(iterate="^states")
```

The container (`tbody`) is the caller's, ordinary grammar. `iterate`
is a machinery word like `store`: consumed, and used as the
expansion's base anchor (stamped on the throw-away wrapper) — the
body's `'.' + label` composes against it, so `^.name` inside the row
resolves to `states.<label>.name`. Cardinality is declared by the
author with `iterate`; `store` never iterates.

## Reactivity shape (design `CMP.7`)

One coarse subscription — the component node's `iterate` pointer — for
the whole collection; the N expansions register nothing. Per-row
granularity is recovered by path arithmetic when the reactive side
lands (`RX`).

Run it from this folder:

```bash
python component_iterate.py
```
