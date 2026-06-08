# 00 — Hello world

The simplest possible page: a heading and a paragraph.

## The page is a builder

A page is a class that subclasses the dialect builder (`HtmlBuilder`)
and writes its document in `main(self, root)`:

```python
class CustomPage(HtmlBuilder):
    def main(self, root):
        body = root.body()
        body.h1("Hello World")
        body.p("My first page with genro-builders.")
```

`root` is the source bag. `root.body()` adds a `<body>`; `body.h1(...)`
and `body.p(...)` add children. Every tag is a method of the grammar.

## Build, then render

```python
page = CustomPage()
page.set_render_target("output.html")
page.create()                 # runs main(): builds the document
page.render(pretty=True)      # renders and writes the target file
print(page.rendered_target)   # reads the written file back
```

- `create()` runs `main` and builds the source.
- `set_render_target("output.html")` registers where the output goes —
  no mode needed, an `HtmlBuilder` renders html by default.
- `render()` renders the source and writes it to the target file.
- `rendered_target` reads that file back, so you can print or inspect
  the result without re-rendering.

## Output

See `output.html`.
