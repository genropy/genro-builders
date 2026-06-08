# 05 — Pointers and templates

A **pointer** binds a node to a datum: instead of a literal, you write a
path and the value is pulled from the page data at render time. This
example shows the pull side only — the data is seeded once and rendered
statically. Reacting to *changes* is a later topic.

> Run it: `python 05_pointers.py` (writes `05_pointers.html`).

## Seeding data

On a plain `HtmlBuilderHandler` you seed data with `self.data.set_item`,
typically in `setup()` (which runs before `main`):

```python
def setup(self):
    self.data.set_item("page.title", "Hello")
```

The path here is **absolute** (`page.title`). Pointers inside the
document are usually **relative** to a `datapath` scope (see below).

## Pointer as value vs as attribute

A pointer can be the node's value or any attribute:

```python
body = root.body(datapath="page")
body.h1("^.title")                       # value  <- page.title
body.div("boxed", color="^.color")       # attr   <- page.color
```

`datapath="page"` opens the scope, so `^.title` means `page.title`.

## `^` vs `=`

Both resolve to the same value when you render:

```python
body.div("lazy ^",  color="^.color")
body.div("eager =", color="=.color")
```

The difference is **reactive**, not in the value: `^` is lazy and `=` is
eager in how the dependency is registered for later updates. At a static
`create()` + `render()` they are indistinguishable — both print the
current datum.

## Templates: `${name}`

A `${name}` placeholder weaves a *resolved attribute* into a string. The
referenced name must be another attribute on the same node:

```python
body.div("themed", class_="card ${color}", color="^.color")
# -> class="card danger"   (page.color == "danger")
```

Phase 1 resolves the `^.color` pointer, phase 2 substitutes `${color}`.
An attribute is either a pointer **or** a template, never both at once.
(In the example `color` doubles as a theme name to show the weave; that
is why the inline `style` looks odd — the point is the `class` string.)

A `${name}` whose value is `None` becomes the empty string.

## Missing data

A pointer to a path that was never set resolves to `None`, which renders
as nothing:

```python
body.span("^.subtitle")   # page.subtitle never set -> <span></span>
```

No error, no fallback — the caller decides whether empty is meaningful.

## Takeaways

- A pointer pulls a datum by path; `datapath` sets the scope for the
  relative `^.name` form.
- A pointer works as the node value or as any attribute.
- `^` and `=` read the same value; they differ only in reactive
  registration.
- `${name}` interpolates a resolved attribute into a string; missing or
  `None` becomes empty.
