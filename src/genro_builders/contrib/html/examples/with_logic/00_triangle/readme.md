# 00 — Triangle

Data is not only stored, it can be **computed**. A `dataFormula`
derives a value from other data; flagged `_on_start`, it runs once
during `create()` — the *first calculation* — before any rendering.

## A formula over the data

The logic is a `@staticmethod` on the page; the `dataFormula` element
wires it to the data:

```python
class CustomPage(HtmlBuilder):
    @staticmethod
    def triangle_area(base, height):
        return base * height / 2

    def setup(self, data):
        data.set_item("base", 10)
        data.set_item("height", 4)

    def main(self, root):
        body = root.body()
        body.dataFormula(
            destination="area", func="triangle_area",
            base="^base", height="^height", _on_start=True,
        )
        body.div("^base")
        body.div("^height")
        body.div("^area")
```

- `func="triangle_area"` names the `@staticmethod` to call.
- `base="^base"`, `height="^height"` are the **bindings**: pointers
  resolved and passed to the function by keyword.
- `destination="area"` is where the result is written (`area` in the
  flat datastore).
- `_on_start=True` makes it run at `create()`.

`area` does not exist until the formula runs; afterwards `^area` reads
the computed `20.0`. A `dataFormula` is pure (no side effects) — for
side effects use `dataController`.

## First calculation, not reactivity

`create()` runs `setup` → `main` → first calculation. The formula fires
once, at build time. Recomputing on later data changes (reactivity) is a
separate, live-mode concern — not exercised here.

## Output

See `output.html`.
