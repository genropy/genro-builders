# 02 — Controller macros

A `dataController` runs **side-effecting** logic (unlike a pure
`dataFormula`). Inside, the `node` exposes the reactive DSL —
`SET` / `GET` / `PUT` / `FIRE` — to read and write the data.

## Setter seeds, controller acts

```python
class CustomPage(HtmlBuilder):
    @staticmethod
    def init_box(node, start):
        node.SET(".count", start)                    # write (origin)
        node.PUT(".quiet", node.GET(".count") + 1)   # quiet write + read
        node.FIRE(".ping")                           # event, not stored

    def main(self, root):
        body = root.body()
        box = body.div(datapath="box")
        box.dataSetter(".start", 7)
        box.dataController(func="init_box", start="^.start", _on_start=True)
        box.span("^.start")
        box.span("^.count")
        box.span("^.quiet")
        box.span("^.ping")
```

- `dataSetter(".start", 7)` seeds `box.start = 7`.
- `dataController(func="init_box", start="^.start")` calls
  `init_box(node, start=7)`. The func is a `@staticmethod`; `node` is
  passed explicitly (so the macros write relative to it).

## The four macros

All four take a path relative to `node` (`.x` → `box.x`):

- **`SET(path, value)`** — write; declares itself the origin of the
  change. Here `count = 7`.
- **`GET(path)`** — read. `GET(".count")` returns `7`.
- **`PUT(path, value)`** — quiet write (does NOT declare itself origin),
  for writes that should not bounce back on a reactive widget. Here
  `quiet = 8`.
- **`FIRE(path)`** — fire an **event**, not a stored value: it flows
  through the bag's subscribe pipeline as a trigger but is *not*
  persisted. So `^.ping` reads back nothing — the last `<span>` is empty.

## Output

See `output.html` — note the empty last span: `FIRE` left no value.
