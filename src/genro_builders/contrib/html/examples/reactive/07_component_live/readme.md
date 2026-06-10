# 07 — Component live

The reactive shape of components (`CMP.7`): the expansion's pointers
are **never** in the pointer_map — the component node holds ONE coarse
subscription, its anchor (`iterate="^states"`). This page proves that
every mutation INSIDE the collection reaches that reader and
re-renders, even though no reader is registered on the mutated path
itself.

## Three mutations, one subscription

```python
def change_00_update_a_field(self, source, data):
    data.set_item("main.states.QLD.capital", "BRISBANE")

def change_01_add_an_item(self, source, data):
    data.set_item("main.states.NSW.name", "New South Wales")
    data.set_item("main.states.NSW.capital", "Sydney")

def change_02_remove_an_item(self, source, data):
    data.del_item("main.states.VIC")
```

- a **field** of one item changes → the row re-renders with the new
  value;
- a **new item** appears → a new row;
- an **item is removed** → its row disappears.

The event machinery classifies the component node as a ``child``
reader (the mutated path starts with the registered anchor): the
coarse subscription catches the fine mutation. At reactivity Level 0
the whole page re-renders; the per-block refinement (re-render only
the QLD row, addressed by path arithmetic on the residual —
`QLD.capital` → label `QLD`) belongs to the partial-render step of
the `RX` roadmap.

Run it from this folder:

```bash
python component_live.py
```
