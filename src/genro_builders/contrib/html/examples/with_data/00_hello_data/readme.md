# 00 — Hello data

The page text is no longer hard-coded: it comes from the **data**.

## A page with data

A builder that reads data declares `setup(self, data)` to seed its data
segment, and reads it in `main` through a **pointer** (`^path`):

```python
class CustomPage(HtmlBuilder):
    def setup(self, data):
        data.set_item("message", "Hello Folk")

    def main(self, root):
        root.body().h1("^message")
```

`^message` is a pointer: at render time it is resolved against the data
and replaced by its value (`Hello Folk`).

## Create, then render

The data lives on the builder itself: `page.data` IS the store. Nothing
needs mounting:

```python
page = CustomPage()
page.create()
page.set_render_target("output.html")
page.render(pretty=True)
print(page.rendered_target)
```

- `create()` runs `setup` (seeds the data) then `main` (builds the
  source), then computes the data-elements in document order.
- The store is flat: `message` is addressed as `message`, with no
  leading segment.
- `render()` resolves the pointers and writes the target file.

## Output

See `output.html`.
