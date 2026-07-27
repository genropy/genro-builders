# CSS grammar (level 1)

**Last Updated**: 2026-07-27
**Status**: 🟢 APPROVATO — allineato al contratto v0.9.0 (renderer-side chain landed 2026-05-30).
**Maintainer**: subtask `css_builder/` (closed 2026-05-12).

CSS level 1 grammar. Covers rules, selectors, custom properties,
and the `@media` / `@supports` / `@import` at-rules.

## Purpose

Produce CSS stylesheets programmatically. Pairs with `CssRenderer`
for serialization. Supports the round-trip via
`CssBuilder.from_css(...)` (parse CSS source into builder code).

## Quick start

```python
from genro_builders.contrib.css import CssBuilder


class Theme(CssBuilder):
    def main(self, root):
        sheet = root.stylesheet()
        cards = sheet.selectorList()
        cards.selector(class_="card")
        cards.selector(class_="panel")
        cards.rule(color="red", padding="10px")
        sheet.cssvar("primary", value="#3498db")


t = Theme(); t.create()
print(t.render())
```

Output:

```css
.card, .panel {
  color: red;
  padding: 10px;
}
:root {
  --primary: #3498db;
}
```

The selector comes first and the `rule` carries its properties — a
`rule` is the property block OF a selector, not its container. A
`cssvar` at stylesheet level is hoisted into `:root`.

## Elements

| Element | Type | Sub-tags | Notes |
|---------|------|----------|-------|
| `stylesheet` | container | `selector,selectorList,cssvar,importcss` | Top-level shell. Mandatory only when the document has `@import`. |
| `selector` | container | `rule,cssvar,selector` | A selector clause (`.card`, `#main`, …). Nest a `selector` inside for CSS Nesting. |
| `selectorList` | container | `selector,rule,cssvar` | Several selectors sharing one `rule` — emitted as `.card, .panel`. |
| `rule` | leaf | — | The property block OF its parent selector. Properties are kwargs; `_` becomes `-`. |
| `cssvar` | leaf | — | A CSS custom property (`--name: value`). At stylesheet level it is hoisted into `:root`. |
| `importcss` | leaf | — | `@import url(...)` at the top of a stylesheet. |

`@media` and `@supports` are passed as **kwargs** on `rule`, not as
separate elements: `rule(media="(max-width: 600px)", ...)`.

## Common patterns

### Property declarations as kwargs

A `rule` accepts CSS properties as kwargs. Hyphenated CSS names use
underscore in Python:

```python
sheet.rule(color="red", font_size="14px", text_align="center")
```

The renderer converts `font_size` → `font-size` on output.

### Selectors as children

Each selector is an explicit child element:

```python
rule = sheet.rule(color="red")
rule.selector(class_="card")
rule.selector(class_="panel")
rule.selector(_id="main")
```

This produces a selector list: `.card, .panel, #main { color: red; }`.

The `class_`, `id`, `attr` kwargs map to CSS selector syntax (a
class, an id, an attribute selector); `classes` takes a list for a
multi-class compound. Pseudo-classes/elements attach directly inside
`class_` (e.g. `class_="card:hover"`); anything the structured kwargs
can't express goes through the opaque `raw` suffix.

### Chaining with `._`

```python
sheet.rule(color="red")\
     .selector(class_="card")\
     ._.selector(class_="panel")\
     ._.cssvar("primary", value="#3498db")
```

See [../builders/patterns.md](../builders/patterns.md).

### Round-trip from CSS source

The builder exposes two classmethods for the reverse direction:

```python
from genro_builders.contrib.css import CssBuilder

# Parse a CSS string into builder Python source:
python_code = CssBuilder.from_css(".card { color: red; }")

# Or parse a file:
python_code = CssBuilder.from_css_file("theme.css")
```

The output is a complete Python module containing a
`CssBuilder` subclass whose `main(self, root)` rebuilds the
input.

## Render

CSS rendering does not use the universal `rendered_item` walk
because CSS needs top-level composition (cssvar grouping,
`@import` ordering, nested `@media`/`@supports` blocks). The CSS
renderer overrides `RendererBase.render(source, **opts)` with a
top-level dispatch that calls into internal helpers
(`_render_top_sequence`, `_render_top_node`, ...) and emits a
stylesheet; `CssBuilder.render` drives this whole-stylesheet
walk instead of the generic `render_children`. The result is still
finalized through the standard `finalize` (a single method: it joins
the fragments and consumes the target).

The only mode is `css`. Output is multi-line, indented with two
spaces, one property per line. No minification mode yet.

## Validation rules

- `selector` kwargs are validated **eagerly** with regex: invalid
  selector syntax raises at `create()` time.
- `rule` rejects unknown CSS shorthand kwargs only when explicitly
  spelled out by the schema; most kwargs pass through as
  declarations.
- `importcss` only valid at the top of a `stylesheet`.

Validation errors raise `ValueError` at `create()` time with a
clear pointer to the offending kwarg.

## Worked examples

`01_introduction/` under
[src/genro_builders/contrib/css/examples/](https://github.com/genropy/genro-builders/tree/main/src/genro_builders/contrib/css/examples/)
is a three-view example covering rules, selector lists, custom
properties, and `@media` kwargs.

## Known limitations

- At-rules beyond `@media`, `@supports`, `@import` are not
  supported in level 1: `@keyframes`, `@font-face`, `@property`,
  `@layer`, `@scope` will be handled in a future subtask.
- No CSS nesting (the level-3 nested rules proposal). Each rule is
  a separate top-level child of the stylesheet.
- No source maps.
- No CSS minification mode.

## References

- Source: `src/genro_builders/contrib/css/`.
- Renderer: `src/genro_builders/contrib/css/css_renderer.py`.
- Schema: `src/genro_builders/contrib/css/css_elements.py`.
- Reverse parser: `src/genro_builders/contrib/css/_reverse.py`.
- Contract: `roadmap/architecture-contract.md`.
