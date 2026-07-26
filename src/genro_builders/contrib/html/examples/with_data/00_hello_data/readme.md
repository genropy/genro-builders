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

## Mount the page on a handler

The data lives on a `BuilderHandler`. Mounting the page connects its
pointers to that data:

```python
page = CustomPage()
handler = BuilderHandler()
handler.add_builder(page)         # page.data IS the store
page.set_render_target("output.html")
page.render(pretty=True)
print(page.rendered_target)
```

- `add_builder(page)` mounts the page and creates it. One handler drives
  one builder, and the store is flat: `message` is addressed as
  `message`, with no leading segment.
- Mounting runs `create()`: `setup` (seeds the data) then `main` (builds
  the source), then the first calculation of the data-elements.
- `render()` resolves the pointers and writes the target file.

## Output

See `output.html`.
