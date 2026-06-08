# 03 — Common segment

The handler owns one datastore split into **segments**: every mounted
builder gets its own (`main`), plus a shared **common** segment named
`_`. Use it for data not owned by a single page (site name, current
user, theme).

## Seed the common segment on the handler

The handler subclass overrides `setup(self, data)` — it receives the
common segment:

```python
class SiteHandler(BuilderHandler):
    def setup(self, data):
        data.set_item("company", "Softwell S.r.l.")
```

## Read it from the page with `_:`

```python
class CustomPage(HtmlBuilder):
    def setup(self, data):
        data.set_item("title", "Welcome")

    def main(self, root):
        body = root.body()
        body.h1("^title")
        body.footer("^_:company")
```

`^title` reads the page's own segment (`main.title`). `^_:company` uses
the `volume:` form — `_` is the volume, so it reads `_.company` from the
common segment instead of `main`.

## Output

See `output.html`.
