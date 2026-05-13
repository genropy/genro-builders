# CssBuilder

CSS source builder (level 1). The dialect uses a **selector-first
model**: each selector is the top-level container of its case,
holding the property rule and any media/supports variants.
Multiple selectors that share a block use an explicit
`selector_list`. CSS Nesting is supported through nested
selectors.

## Install

```bash
pip install genro-builders
```

## Quick start

```python
from genro_builders.contrib.css import CssBuilderHandler


class Theme(CssBuilderHandler):
    def main(self, root):
        s = root.selector(_class="card")
        s.rule(color="white", background_color="#3498db", padding="12px")


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

| Element         | Purpose                                       | Children                                              |
|-----------------|-----------------------------------------------|-------------------------------------------------------|
| `stylesheet`    | Optional top-level container                  | `selector`, `selector_list`, `cssvar`                 |
| `selector`      | One selector, container of the case           | `rule`, `cssvar`, nested `selector`                   |
| `selector_list` | Comma-separated selector-list sharing a block | `selector` (the entries) + `rule`, `cssvar`           |
| `rule`          | A property block; optional `media`/`supports` | none                                                  |
| `cssvar`        | A CSS custom property declaration             | none                                                  |

### selector

`selector(...)` accepts structured kwargs for the compound form
plus a `raw` kwarg for the rest:

| Kwarg     | Type                       | Renders as              | Example                                  |
|-----------|----------------------------|-------------------------|------------------------------------------|
| `tag`     | `str`                      | `tagname`               | `tag="div"` → `div`                      |
| `id`      | `str`                      | `#id`                   | `id="main"` → `#main`                    |
| `_class`  | `str` (one class)          | `.class`                | `_class="card"` → `.card`                |
| `classes` | `list[str]`                | `.a.b.c`                | `classes=["card","featured"]` → `.card.featured` |
| `attr`    | `dict[str, str \| None]`   | `[name="v"]` / `[name]` | `attr={"type":"text"}` → `[type="text"]` |
| `raw`     | `str`                      | suffix, space-separated | `raw="> .icon"` → `<compound> > .icon`   |

Composition order: `tag → id → classes → attr`, then `raw`
appended with a leading space if a compound precedes it.
`_class` and `classes` are mutually exclusive.

Pseudo-classes and pseudo-elements attach directly inside
`_class`:

```python
root.selector(_class="card:hover")
root.selector(_class="btn::before")
```

`raw` is the unchecked escape hatch for combinators, functional
pseudo-classes, and anything not covered by the structured form:

```python
root.selector(raw=".card:not(.disabled)")
root.selector(_class="card", raw="> .icon")
```

### selector_list

When several selectors share the same rule and variants, use
`selector_list` as the container:

```python
sl = root.selector_list()
sl.selector(_class="card")
sl.selector(_class="panel")
sl.selector(_class="dialog")
sl.rule(color="white")
```

```css
.card, .panel, .dialog {
  color: white;
}
```

### rule

Property block. Underscores in kwarg names are converted to
hyphens at render time. Values are stringified verbatim.

```python
s = root.selector(_class="x")
s.rule(background_color="#fff", font_size="12px")
```

### media and supports

A rule may carry optional ``media`` and ``supports`` kwargs.
Each is a free-form string with the full condition (a feature, a
type, or both combined). At render time the rule is lifted into
a ``@media`` and/or ``@supports`` block that re-uses the parent
selector:

```python
s = root.selector(_class="card")
s.rule(width="300px")
s.rule(media="(max-width: 600px)", width="100%")
s.rule(media="screen and (max-width: 600px)", padding="8px")
s.rule(media="print", color="black")
s.rule(supports="(display: grid)", display="grid")
```

```css
.card {
  width: 300px;
  @media (max-width: 600px) {
    .card { width: 100%; }
  }
  @media screen and (max-width: 600px) {
    .card { padding: 8px; }
  }
  @media print {
    .card { color: black; }
  }
  @supports (display: grid) {
    .card { display: grid; }
  }
}
```

Multiple rules under the same selector that share the **same**
``(media, supports)`` pair are merged into a single block.
When both kwargs are present on the same rule, ``@supports``
wraps the ``@media`` block.

### cssvar

CSS custom property declaration. Lives inside a selector
(typically `:root`).

```python
rt = root.selector(raw=":root")
rt.cssvar("primary-color", value="#3498db")
rt.cssvar("spacing", value="8px")
```

```css
:root {
  --primary-color: #3498db;
  --spacing: 8px;
}
```

Consume from property values as a regular `var(--name)`:

```python
root.selector(_class="branded").rule(color="var(--primary-color)")
```

## CSS Nesting

Attach nested selectors inside a selector to get native CSS
nesting:

```python
card = root.selector(_class="card")
card.rule(padding="8px")
title = card.selector(_class="title")
title.rule(font_size="18px")
hover = card.selector(raw="&:hover")
hover.rule(background_color="#eef")
```

```css
.card {
  padding: 8px;
  .title {
    font-size: 18px;
  }
  &:hover {
    background-color: #eef;
  }
}
```

Composition rules (resolved by the browser at parse time):

- a nested selector that does **not** start with `&` is a
  **descendant** of the parent: `.title` inside `.card` →
  `.card .title`;
- a nested selector that **starts with `&`** binds tightly to the
  parent: `&:hover` inside `.card` → `.card:hover`;
- a parent selector-list (`.a, .b`) distributes: `.a, .b { .x
  { ... } }` → `.a .x, .b .x`.

Native CSS Nesting requires Chrome 112+, Safari 16.5+, Firefox
117+ (2023). For older browsers, write the selectors flat.

## Comments

Any element accepts an optional `comment="..."` kwarg:

- length ≤ 60 chars → inline `/* ... */` at the end of the last
  declaration of the block;
- length > 60 chars → block `/* ... */` on its own line above
  the element.

```python
s = root.selector(_class="alert", comment="warning state")
s.rule(color="red")
```

```css
.alert {
  color: red; /* warning state */
}
```

## Rendering

```python
page.render()                            # pretty (default)
page.render(pretty=False)                # single line
page.render(pretty=True, indent="    ")  # 4-space indent
```

The CSS renderer does not go through `render_xml` — CSS is not
XML. `render_css` emits the `selector-list { prop: value; ... }`
syntax directly.

## Validation

Validation is eager: malformed structured kwargs raise
`ValueError` at render time with a clear message.

| Kwarg                              | Regex                                |
|------------------------------------|--------------------------------------|
| `tag`                              | `^[a-zA-Z][\w-]*$`                   |
| `id`                               | `^[a-zA-Z_-][\w-]*$`                 |
| `_class`, each `classes` entry     | `^[a-zA-Z_-][\w-]*(:{1,2}[\w-]+)*$`  |
| attribute name in `attr`           | `^[a-zA-Z_-][\w-]*$`                 |

`raw` is not validated.

## Example

A complete handler demonstrating every level-1 feature:

```python
from genro_builders.contrib.css import CssBuilderHandler


class Theme(CssBuilderHandler):
    def main(self, root):
        sheet = root.stylesheet()

        # CSS custom properties
        rt = sheet.selector(raw=":root")
        rt.cssvar("brand", value="#3498db", comment="brand color")
        rt.cssvar("spacing", value="8px")

        # Single selector + rule
        card = sheet.selector(_class="card")
        card.rule(
            background_color="var(--brand)",
            color="white",
            padding="var(--spacing)",
            border_radius="6px",
        )

        # Selector-list
        shared = sheet.selector_list()
        shared.selector(_class="card")
        shared.selector(_class="panel")
        shared.selector(_class="dialog")
        shared.rule(font_family="sans-serif", line_height="1.5")

        # Media variant
        responsive = sheet.selector(_class="responsive")
        responsive.rule(width="300px")
        responsive.rule(media="(max-width: 600px)", width="100%")

        # Nesting
        nested = sheet.selector(_class="nested")
        nested.rule(padding="8px")
        title = nested.selector(_class="title")
        title.rule(font_size="18px")
        hover = nested.selector(raw="&:hover")
        hover.rule(background_color="#eef")


theme = Theme()
theme.create()
theme.build()
print(theme.render())
```

See [examples/](examples/) for a guided tour as both a script and
a Jupyter notebook.
