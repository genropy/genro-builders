# 05 — Containers

A `@container` is a reusable block invoked **from a node**, not
through `self`. Compare with `04_methods`: there you wrote
`self.card(body, ...)`; here you write `body.card(...)` and the node it
was called on arrives as the first argument (by convention, `pane`).

```python
class CustomPage(HtmlBuilder):
    @container
    def card(self, pane, title, body, color="#3498db"):
        box = pane.div(class_="card", border_top=f"3px solid {color}")
        box.h3(title)
        box.p(body)

    def main(self, root):
        body = root.body()
        body.card("Designer", "Alice", color="#e74c3c")
```

`body.card(...)` is not an HTML tag — the grammar has no `card`, so it
falls back to the container registered on the builder, called with
`pane=body`.

## Naming (legacy parity)

- a prefix before the first `_` is stripped: `ui_badge` → `badge`;
- dispatch is case-insensitive: `body.Badge(...)` hits the same block;
- pass an explicit name with `@container("alias")`.

## Output

See `output.html`.
