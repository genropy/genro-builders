# 01 — Nested data

Data is a tree, not a flat dict. A pointer can reach a **nested** path
with dots.

## Seed and read a dotted path

```python
class CustomPage(HtmlBuilder):
    def setup(self, data):
        data.set_item("user.name", "Ada Lovelace")
        data.set_item("user.email", "ada@example.com")

    def main(self, root):
        body = root.body()
        body.h1("^user.name")
        body.p("^user.email")
```

`set_item("user.name", ...)` creates the `user` sub-bag and stores
`name` inside it. The pointer `^user.name` walks the same path to read
it back. `user` is one node holding both `name` and `email`.

## Output

See `output.html`.
