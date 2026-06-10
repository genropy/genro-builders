# 08 — Nested component live

Fractal composition meets reactivity: `state_card` iterates the
states, and inside each card `city_item` iterates that state's
cities. Neither expansion registers a single pointer — the ONLY
subscription in the map is the outermost component's anchor
(`^states`).

## Deep mutations, one subscription

```python
def change_00_rename_a_city(self, source, data):
    data.set_item("main.states.QLD.cities.bri.name", "BRISBANE")
```

The mutated path is two expansion levels below the anchor, and no
reader is registered on it (nor anywhere inside the collection). The
match is by **prefix**: `main.states.QLD.cities.bri.name` starts with
the registered `main.states`, so the outer component node is found as
a `child` reader and the page re-renders — whatever the depth.

The other changes prove the structural cases: a new city in an
existing state, a whole new state (with its cities — the nested
iterate picks them up on the same render), a removed city.

## Why this matters

This is the recursive form of `CMP.7` (design D10): "coarse
subscription, fine resolution" holds across nesting — the
subscription cost does not grow with the depth or the size of the
expansions. The per-block refinement (re-render only the QLD card, or
only the renamed `<li>`) is path arithmetic on the residual, planned
with partial render in the `RX` roadmap.

Run it from this folder:

```bash
python nested_component_live.py
```
