# 10 — Component nesting

Components compose **fractally**: a component's body can use other
components — normal or iterate — without limit. Nothing new to learn:
the expansion is built with the same grammar as any source, so the
walk's dispatch applies recursively.

## A component inside a component

```python
class CommonComponents:

    @component
    def cityItem(self, root, node_label=None):
        li = root.li(datapath="." + node_label)
        li.span("^.name")

    @component
    def stateCard(self, root, node_label=None):
        card = root.div(datapath="." + node_label, class_="state")
        card.h3("^.name")
        card.ul().cityItem(iterate="^.cities")
```

The inner `iterate` is **relative**: `'^.cities'` composes against
the card's item, so each state's card iterates that state's own
cities — `states.QLD.cities`, `states.VIC.cities`, ...

## One node, two levels of expansion

```python
body.stateCard(iterate="^states")
```

The source holds ONE node. At render time: one card per state, and
inside each card one item per city. Datapaths stack across the
expansion levels exactly as they do in an ordinary tree.

See `11_component_recursion` for the limit case: a component whose
body uses itself.

Run it from this folder:

```bash
python component_nesting.py
```
