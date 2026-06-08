# 02 — Relative datapath

A container can fix a **datapath**; its children then read with a
leading `.`, relative to that path. Less repetition, clear scoping.

## A container with a datapath

```python
class CustomPage(HtmlBuilder):
    def setup(self, data):
        data.set_item("invoice.number", "INV-001")
        data.set_item("invoice.total", 1250)

    def main(self, root):
        body = root.body()
        section = body.div(datapath="invoice")
        section.h1("^.number")
        section.p("^.total")
```

`div(datapath="invoice")` anchors the section to `invoice`. Inside it,
`^.number` resolves to `invoice.number` and `^.total` to
`invoice.total` — the leading `.` means "relative to the nearest
ancestor datapath". Move the data under a different key and only the
`datapath` changes, not every child.

## Output

See `output.html`.
