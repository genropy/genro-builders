# 11 — Component recursion

The limit case of fractal composition: a component whose body uses
**itself**. Legitimate and useful — trees are everywhere (folders,
org charts, menus).

## The self-recursive block

```python
class CommonComponents:

    @component
    def treeItem(self, root, node_label=None):
        li = root.li(datapath="." + node_label)
        li.span("^.name")
        li.ul().treeItem(iterate="^.children")
```

## Data-driven termination

Recursion stops where the data stops: a leaf has no `.children`, the
`iterate` finds an empty collection, zero blocks are produced, the
descent ends. The mode is declared by the author (the presence of
`iterate`), never decided by the data — an empty collection means
"zero rounds", not "fall back to a single expansion".

A self-reference that does NOT consume data would loop at render
time: that is the author's bug, exactly like an infinite `while`.

Run it from this folder:

```bash
python component_recursion.py
```
