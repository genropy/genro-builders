# CssBuilder

CSS source builder (level 1): rules with property declarations,
selector-lists, CSS custom properties (variables), comments, and
both fragment and full-stylesheet output.

## Install

```bash
pip install genro-builders
```

## Quick start

```python
from genro_builders.contrib.css import CssBuilderHandler


class Theme(CssBuilderHandler):
    def main(self, root):
        r = root.rule(color="white", background_color="#3498db", padding="12px")
        r.selector(_class="card")


theme = Theme()
theme.create()
theme.build()
print(theme.render())
```

Output:

```css
.card {
  color: white;
  background-color: #3498db;
  padding: 12px;
}
```

## Grammar

Four elements:

| Element      | Purpose                                          | Children          |
|--------------|--------------------------------------------------|-------------------|
| `stylesheet` | Optional top-level container for a list of rules | `rule`            |
| `rule`       | A CSS rule (selectors + properties)              | `selector`, `cssvar` |
| `selector`   | One entry of a rule's selector-list              | leaf              |
| `cssvar`     | A CSS custom property declaration                | leaf              |

`rule` can live inside `stylesheet` or directly at the bag root.
The latter produces a **fragment** — useful when the CSS is meant
to be embedded inside another document.

### stylesheet

Top-level container. Use it when you want one rendered document
containing a list of rules.

```python
sheet = root.stylesheet()
sheet.rule(...).selector(...)
sheet.rule(...).selector(...)
```

### rule

`rule(...)` accepts CSS properties as kwargs. Underscores in kwarg
names are converted to hyphens at render time.

```python
r = root.rule(color="red", font_size="14px", background_color="#fff")
```

Property values are stringified verbatim — no unit injection.
Pass `padding="8px"`, not `padding=8`.

Every rule must declare at least one `selector` child. Calling
`render()` on a rule with no selectors raises `ValueError`.

### selector

A rule has one or more `selector` children. Multiple selectors
become a comma-separated selector-list:

```python
r = root.rule(color="red")
r.selector(_class="card")
r.selector(_class="panel")
r.selector(_class="dialog")
```

```css
.card, .panel, .dialog {
  color: red;
}
```

`selector(...)` accepts **structured kwargs** for the compound
form (multiple matchers on the same element) and a `raw` kwarg
for the rest:

| Kwarg     | Type                       | Renders as              | Example                                  |
|-----------|----------------------------|-------------------------|------------------------------------------|
| `tag`     | `str`                      | `tagname`               | `tag="div"` → `div`                      |
| `id`      | `str`                      | `#id`                   | `id="main"` → `#main`                    |
| `_class`  | `str` (one class)          | `.class`                | `_class="card"` → `.card`                |
| `classes` | `list[str]`                | `.a.b.c`                | `classes=["card","featured"]` → `.card.featured` |
| `attr`    | `dict[str, str \| None]`   | `[name="v"]` / `[name]` | `attr={"type":"text"}` → `[type="text"]` |
| `raw`     | `str`                      | suffix, space-separated | `raw="> .icon"` → `<compound> > .icon`   |

Composition order is fixed by the renderer: `tag → id → classes →
attr`, then `raw` appended with a leading space if a compound
precedes it. The caller may pass kwargs in any order.

`_class` and `classes` are mutually exclusive; passing both raises
`ValueError`.

Pseudo-classes and pseudo-elements (`:hover`, `::before`, ...) can
be attached directly inside `_class`:

```python
r.selector(_class="card:hover")       # → .card:hover
r.selector(_class="btn::before")      # → .btn::before
r.selector(_class="card:hover:focus") # → .card:hover:focus
```

`raw` is the unchecked escape hatch for combinators, functional
pseudo-classes, and anything not covered by the structured form:

```python
r.selector(raw=".card:not(.disabled)")  # → .card:not(.disabled)
r.selector(raw="nav > ul li a")         # → nav > ul li a
r.selector(_class="card", raw="> .icon")  # → .card > .icon
```

A selector with no kwargs raises `ValueError`.

### cssvar

CSS custom property declaration. Lives as a child of a rule
(typically `:root`).

```python
r = root.rule()
r.selector(raw=":root")
r.cssvar("primary-color", value="#3498db")
r.cssvar("spacing", value="8px")
```

```css
:root {
  --primary-color: #3498db;
  --spacing: 8px;
}
```

The first positional argument is the variable name (without the
`--` prefix; the renderer adds it). Consume the variable from
property values as a regular `var(--name)` string:

```python
sheet.rule(background_color="var(--primary-color)")
```

## Comments

Any element accepts an optional `comment="..."` kwarg. The
renderer picks the position based on length:

- length ≤ 60 chars → inline `/* ... */` at the end of the last
  declaration of the block;
- length > 60 chars → block `/* ... */` on its own line above
  the element.

```python
r = root.rule(color="red", comment="warning state")
r.selector(_class="alert")
```

```css
.alert {
  color: red; /* warning state */
}
```

A longer comment renders as a block:

```python
r = root.rule(
    display="grid",
    comment="Grid layout for the dashboard summary cards; auto-fit + minmax lets cards reflow without media queries",
)
r.selector(_class="dashboard")
```

```css
/* Grid layout for the dashboard summary cards; auto-fit + minmax lets cards reflow without media queries */
.dashboard {
  display: grid;
}
```

Comments on `cssvar` follow the same rule:

```python
r.cssvar("primary", value="#3498db", comment="brand color")
# → --primary: #3498db; /* brand color */
```

## Fluent chaining with `._`

`._` is a property of every `BagNode` in `genro-bag`: from a node
it returns the bag that contains it. Used after a leaf call,
`._` lets you keep adding siblings without breaking the
expression:

```python
root.rule(color="red", font_size="14px") \
    .selector(_class="card")._ \
    .selector(_class="panel")._ \
    .cssvar("primary", value="#3498db")
```

This is equivalent to the form with an intermediate variable.
Use whichever reads better in context.

## Rendering

```python
page.render()                         # pretty-printed (default)
page.render(pretty=False)             # single line
page.render(pretty=True, indent="    ")  # 4-space indent
```

The CSS renderer does not go through `render_xml` — CSS is not
XML. `render_css` emits the `selector-list { prop: value; ... }`
syntax directly.

## Validation

Validation is eager: malformed structured kwargs raise
`ValueError` at render time with a clear message, instead of
producing CSS the browser would silently drop.

Validated patterns:

| Kwarg            | Regex                                |
|------------------|--------------------------------------|
| `tag`            | `^[a-zA-Z][\w-]*$`                   |
| `id`             | `^[a-zA-Z_-][\w-]*$`                 |
| `_class`, each `classes` entry | `^[a-zA-Z_-][\w-]*(:{1,2}[\w-]+)*$` |
| attribute name in `attr` | `^[a-zA-Z_-][\w-]*$`         |

`raw` is not validated.

Common errors:

- `_class="card featured"` — spaces are not allowed inside a
  class name; use `classes=["card","featured"]`.
- `_class="card.featured"` — dots are not allowed inside a
  class name; use `classes=["card","featured"]`.
- `_class="x"` and `classes=["y","z"]` together — mutually
  exclusive.
- `selector()` with no kwargs — at least one of `tag`, `id`,
  `_class`, `classes`, `attr`, `raw` is required.
- `rule()` with no `selector` child — every rule needs at least
  one selector.

## Examples

A complete handler demonstrating fragments, stylesheets, multi-
selectors, variables, and comments:

```python
from genro_builders.contrib.css import CssBuilderHandler


class Theme(CssBuilderHandler):
    def main(self, root):
        sheet = root.stylesheet()

        # CSS custom properties
        rt = sheet.rule()
        rt.selector(raw=":root")
        rt.cssvar("brand", value="#3498db", comment="brand color")
        rt.cssvar("spacing", value="8px")

        # Single rule
        card = sheet.rule(
            background_color="var(--brand)",
            color="white",
            padding="var(--spacing)",
            border_radius="6px",
        )
        card.selector(_class="card")

        # Selector-list
        shared = sheet.rule(font_family="sans-serif", line_height="1.5")
        shared.selector(_class="card")
        shared.selector(_class="panel")
        shared.selector(_class="dialog")

        # Pseudo-class attached to a class
        hover = sheet.rule(opacity="0.8", comment="hover dim")
        hover.selector(_class="card:hover")

        # Attribute selector
        inp = sheet.rule(padding="4px")
        inp.selector(tag="input", attr={"type": "text"})


theme = Theme()
theme.create()
theme.build()
print(theme.render())
```

```css
:root {
  --brand: #3498db; /* brand color */
  --spacing: 8px;
}
.card {
  background-color: var(--brand);
  color: white;
  padding: var(--spacing);
  border-radius: 6px;
}
.card, .panel, .dialog {
  font-family: sans-serif;
  line-height: 1.5;
}
.card:hover {
  opacity: 0.8; /* hover dim */
}
input[type="text"] {
  padding: 4px;
}
```

See [examples/](examples/) for a guided tour as both a script and
a Jupyter notebook.

## Rule nesting

A `rule` can contain other `rule` nodes as children. Nested rules
are emitted as native CSS Nesting (W3C spec, supported by modern
browsers since 2023). The browser flattens the output at parse
time according to the standard rules.

### Authoring

Attach a nested rule by calling `rule(...)` on the parent rule
node:

```python
card = sheet.rule(padding="8px")
card.selector(_class="card")

title = card.rule(font_size="18px")
title.selector(_class="title")              # descendant: .card .title

hover_title = title.rule(color="blue")
hover_title.selector(raw="&:hover")         # .card .title:hover

icon = card.rule(width="16px")
icon.selector(raw="& > .icon")              # .card > .icon

hover_card = card.rule(background_color="#eef")
hover_card.selector(raw="&:hover")          # .card:hover
```

Output:

```css
.card {
  padding: 8px;
  .title {
    font-size: 18px;
    &:hover {
      color: blue;
    }
  }
  & > .icon {
    width: 16px;
  }
  &:hover {
    background-color: #eef;
  }
}
```

Nested rules can be arbitrarily deep; each level adds one unit
of indentation in pretty mode.

### Selector composition (browser rules)

The output preserves the selectors verbatim — composition happens
at parse time in the browser:

- A nested selector that does **not** start with `&` is a
  **descendant** of the parent selector. `.title` inside
  `.card { ... }` resolves to `.card .title`.
- A nested selector that **starts with `&`** binds tightly to the
  parent. `&` is replaced by the parent's selector. `&:hover`
  resolves to `.card:hover`; `& > .icon` to `.card > .icon`.
- A parent selector-list (`.a, .b`) distributes: `.a, .b { .x
  { ... } }` resolves to `.a .x, .b .x { ... }`.

Use `selector(raw="...")` for any nested selector that contains
`&`, combinators (`>`, `+`, `~`), or a pseudo-class attached to
the parent. Use the structured form (`tag`, `_class`, `classes`,
etc.) for plain descendants.

### Browser compatibility

Native CSS Nesting requires Chrome 112+, Safari 16.5+, Firefox
117+ (all 2023). For environments that need older-browser
support, write the rules flat (without nesting): the builder
emits them unchanged.
