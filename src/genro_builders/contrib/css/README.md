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
from genro_builders.contrib.css import CssBuilder


class Theme(CssBuilder):
    def main(self, root):
        s = root.selector(class_="card")
        s.rule(color="white", background_color="#3498db", padding="12px")


theme = Theme()
theme.create()
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
| `class_`  | `str` (one class)          | `.class`                | `class_="card"` → `.card`                |
| `classes` | `list[str]`                | `.a.b.c`                | `classes=["card","featured"]` → `.card.featured` |
| `attr`    | `dict[str, str \| None]`   | `[name="v"]` / `[name]` | `attr={"type":"text"}` → `[type="text"]` |
| `raw`     | `str`                      | suffix, space-separated | `raw="> .icon"` → `<compound> > .icon`   |

Composition order: `tag → id → classes → attr`, then `raw`
appended with a leading space if a compound precedes it.
`class_` and `classes` are mutually exclusive. (The leading-underscore
form `_class` is still accepted but deprecated; prefer `class_`.)

Pseudo-classes and pseudo-elements attach directly inside
`class_`:

```python
root.selector(class_="card:hover")
root.selector(class_="btn::before")
```

`raw` is the unchecked escape hatch for combinators, functional
pseudo-classes, and anything not covered by the structured form:

```python
root.selector(raw=".card:not(.disabled)")
root.selector(class_="card", raw="> .icon")
```

### selector_list

When several selectors share the same rule and variants, use
`selector_list` as the container:

```python
sl = root.selector_list()
sl.selector(class_="card")
sl.selector(class_="panel")
sl.selector(class_="dialog")
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
s = root.selector(class_="x")
s.rule(background_color="#fff", font_size="12px")
```

### media and supports

A rule may carry optional ``media`` and ``supports`` kwargs.
Each is a free-form string with the full condition (a feature, a
type, or both combined). At render time the rule is lifted into
a ``@media`` and/or ``@supports`` block that re-uses the parent
selector:

```python
s = root.selector(class_="card")
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
root.selector(class_="branded").rule(color="var(--primary-color)")
```

## CSS Nesting

Attach nested selectors inside a selector to get native CSS
nesting:

```python
card = root.selector(class_="card")
card.rule(padding="8px")
title = card.selector(class_="title")
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
s = root.selector(class_="alert", comment="warning state")
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
| `class_`, each `classes` entry     | `^[a-zA-Z_-][\w-]*(:{1,2}[\w-]+)*$`  |
| attribute name in `attr`           | `^[a-zA-Z_-][\w-]*$`                 |

`raw` is not validated.

## Example

A complete handler demonstrating every level-1 feature:

```python
from genro_builders.contrib.css import CssBuilder


class Theme(CssBuilder):
    def main(self, root):
        sheet = root.stylesheet()

        # CSS custom properties
        rt = sheet.selector(raw=":root")
        rt.cssvar("brand", value="#3498db", comment="brand color")
        rt.cssvar("spacing", value="8px")

        # Single selector + rule
        card = sheet.selector(class_="card")
        card.rule(
            background_color="var(--brand)",
            color="white",
            padding="var(--spacing)",
            border_radius="6px",
        )

        # Selector-list
        shared = sheet.selector_list()
        shared.selector(class_="card")
        shared.selector(class_="panel")
        shared.selector(class_="dialog")
        shared.rule(font_family="sans-serif", line_height="1.5")

        # Media variant
        responsive = sheet.selector(class_="responsive")
        responsive.rule(width="300px")
        responsive.rule(media="(max-width: 600px)", width="100%")

        # Nesting
        nested = sheet.selector(class_="nested")
        nested.rule(padding="8px")
        title = nested.selector(class_="title")
        title.rule(font_size="18px")
        hover = nested.selector(raw="&:hover")
        hover.rule(background_color="#eef")


theme = Theme()
theme.create()
print(theme.render())
```

See [examples/](examples/) for a guided tour as both a script and
a Jupyter notebook.

## Reverse: from CSS to Python

`CssBuilder` ships a **reverse** facility that parses an existing
CSS source and emits an equivalent `CssBuilder` subclass. It
is meant for migrating legacy CSS into the builder model, or as a
learning aid to see how a hand-written CSS file maps onto the
grammar.

The reverse depends on `tree-sitter` and `tree-sitter-css`. Install
the optional extra:

```bash
pip install 'genro-builders[reverse]'
```

### Entry points

Two classmethods on the builder (a conscious exception to the
project-wide *no-classmethod* rule, since the reverse runs before
any instance exists):

```python
from genro_builders.contrib.css import CssBuilder

# 1. From a string
code = CssBuilder.from_css(css_source)                     # returns str
CssBuilder.from_css(css_source, "out/generated.py")        # writes to file
CssBuilder.from_css(css_source, my_file_like_buffer)       # .write()
CssBuilder.from_css(css_source, my_callable)               # invoked with text

# 2. From a file
code = CssBuilder.from_css_file("theme.css")               # class_name defaults to "Theme"
CssBuilder.from_css_file("theme.css", "out/theme.py")
CssBuilder.from_css_file("theme.css", class_name="Branded")
```

The `dest` parameter follows the same contract as the renderer's
`render_target` (`None` → return string, `str`/`Path` → write to
filesystem creating parent dirs, file-like with `.write` → write,
callable → invoke).

### What is emitted

```python
from genro_builders.contrib.css import CssBuilder


class ReversedCss(CssBuilder):

    def main(self, root):
        sheet = root.stylesheet()
        sheet.importcss(url='reset.css')
        s_1 = sheet.selector(class_='card')
        s_1.rule(color='red', padding='8px')
```

The output **always** opens a `sheet = root.stylesheet()` as its
first statement: the reverse targets whole CSS documents, never
fragments, and `@import` directives require a stylesheet container
by grammar.

### Coverage

| CSS construct                         | Reverse output                                  |
| ------------------------------------- | ----------------------------------------------- |
| `.foo { color: red }`                 | `selector(class_='foo').rule(...)`              |
| `.a, .b { ... }`                      | `selector_list().selector().selector().rule()`  |
| `#main`, `button`                     | `selector(id=...)`, `selector(tag=...)`         |
| `input[type="text"]`                  | `selector(attr={'type': 'text'})`               |
| `.btn:hover`                          | `selector(class_='btn:hover')`                  |
| `.parent .child`, `:not(.x)`          | `selector(raw=...)` (fallback)                  |
| `--brand: #3498db`                    | `cssvar('brand', value='#3498db')`              |
| `@media (max-width: 600px) { ... }`   | `rule(media='(max-width: 600px)', ...)`         |
| `@supports (display: grid) { ... }`   | `rule(supports='(display: grid)', ...)`         |
| `.card { .title { ... } }`            | nested `selector()` (CSS Nesting)               |
| `@import url("foo")`                  | `importcss(url='foo')`                          |
| `@import url("foo") screen ...`       | `importcss(url='foo', media='screen ...')`      |

### Limitations

- **Comments** in the source CSS are dropped (`# D6`). Re-add them
  manually as `comment=...` kwargs if needed.
- **At-rules** beyond `@media` / `@supports` / `@import`
  (`@keyframes`, `@font-face`, `@property`, `@layer` block-form,
  `@scope`, ...) are not in the level-1 grammar; the reverse emits
  a `"# unsupported: ..."` Python comment-string and skips them.
- **`@import` modifiers** `layer(...)` and `supports(...)` are not
  recognised by `tree-sitter-css` 0.25; when present the reverse
  emits a `"# layer/supports modifier not parsed, see source: ..."`
  hint so the user can patch the call by hand.
- **Vendor prefixes** are correctly recognised: `-webkit-foo` →
  `_webkit_foo` kwarg → re-rendered as `-webkit-foo`.
