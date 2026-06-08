# 02 — Nested structure

Real pages are deep trees. Every element call returns the new node, so
you nest by holding it in a local variable and adding children to it.

```python
header = body.header(...)
header.h1("Dashboard")
nav = header.nav()
nav.a("Home", href="#")
```

`body.header(...)` returns the `<header>` node; `header.nav()` returns
the `<nav>` inside it, and so on. The nesting in the output mirrors the
nesting of your variables.

## Building repeated structure

Plain Python drives the structure — a `for` loop builds a grid of cards:

```python
grid = section.div(display="grid", gap="12px")
for title, text in (...):
    card = grid.div(...)
    card.h3(title)
    card.p(text)
```

No special construct: the page is ordinary code that happens to emit a
tree. (This data is hardcoded in the loop — binding a card to live data
comes later, in the `with_data` examples.)

## Output

See `output.html`.
