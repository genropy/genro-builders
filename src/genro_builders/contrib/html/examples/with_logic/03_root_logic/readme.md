# 03 — Root logic

Data-elements are grammar elements, and the grammar works on the
**root bag** exactly as on any node: `root.dataSetter("price", 100)`
maps the positional arguments onto the schema field names
(`destination`, `value`) just like `body.dataSetter(...)` does.

## Data-elements on the root

```python
class CustomPage(HtmlBuilder):
    @staticmethod
    def gross(price, tax):
        return round(price * (1 + tax), 2)

    def main(self, root):
        root.dataSetter("price", 100)
        root.dataSetter("tax", 0.22)
        root.dataFormula(
            destination="total", func="gross",
            price="^price", tax="^tax",
        )
        body = root.body()
        body.div("^total")
```

The setters seed the data at the first calculation, the formula
computes `total`, and the pointers in the body read the results — the
data-elements themselves are transparent to the render.

## Why this example exists

Element creation has two entry points — a node and a bag — and both
must apply the same grammar semantics. This page exercises the bag
entry point on the data-element case (positional field mapping); it
fails if the two paths ever diverge again.

Run it from this folder:

```bash
python root_logic.py
```
