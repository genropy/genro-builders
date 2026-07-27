# 01 — Triangles + total

A plain Python `for` builds five triangles, each with its own data and
area formula; a final formula sums the five areas. All computed at start.

## A loop of scoped containers

`main` is ordinary Python — loop, build, scope with datapaths:

```python
def main(self, root):
    body = root.body()
    triangoli = body.div(datapath="triangoli")        # absolute anchor
    for i in range(1, 6):
        row = triangoli.div(datapath=f".tr{i}")       # relative to triangoli
        row.dataSetter(".base", i * 2)
        row.dataSetter(".height", i)
        row.dataFormula(
            destination=".area", func="triangle_area",
            base="^.base", height="^.height",
        )
        row.span("^.base")
        row.span("^.height")
        row.span("^.area")
    body.dataFormula(
        destination="total", func="sum_areas",
        a1="^triangoli.tr1.area", a2="^triangoli.tr2.area",
        a3="^triangoli.tr3.area", a4="^triangoli.tr4.area",
        a5="^triangoli.tr5.area",
    )
    body.div("^total")
```

## Datapath scoping

- `div(datapath="triangoli")` is **absolute**: it anchors the subtree.
- `div(datapath=f".tr{i}")` is **relative**: each row resolves under
  `triangoli` (→ `triangoli.tr1`, `triangoli.tr2`, …).
- Inside a row, `.base` / `.height` / `.area` are relative to that row.

A relative datapath needs an absolute ancestor to anchor it — here
`triangoli` provides it.

## Order of the first calculation

The five `.area` formulas are declared before `total`, so at `create()`
they run first; `sum_areas` then reads the five computed areas
(`1 + 4 + 9 + 16 + 25 = 55.0`). `dataSetter`s seed the bases/heights
before any formula reads them.

## Output

See `output.html`.
