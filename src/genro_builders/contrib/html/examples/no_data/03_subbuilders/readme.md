# 03 — Sub-builders

A sub-builder switches the active grammar mid-document. The host page is
HTML, but inside an `<svg>` the SVG grammar takes over — and HTML can be
re-entered inside the SVG.

## HTML hosting SVG

```python
s = body.svg(width=200, height=80, viewBox="0 0 200 80")
s.circle(cx=40, cy=40, r=30, fill="#e74c3c")
s.rect(x=90, y=20, width=90, height=40, fill="#3498db")
```

`body.svg(...)` opens the SVG dialect: from `s` on, `circle` and `rect`
are valid (they belong to SVG, not HTML). The node carries the SVG
builder on its `_builder` slot, so the descent resolves SVG tags.

## SVG hosting HTML

```python
overlay = s2.html(x=20, y=20, width=320, height=80)
card = overlay.div(color="white", padding="8px")
card.p("HTML rendered inside an SVG.")
```

`s2.html(...)` re-enters HTML inside the SVG. The framework wraps the
HTML subtree in `<foreignObject>` (with the xhtml namespace) at render
time — the user only writes `html`.

## Output

See `output.html`.
