# CSS grammar (level 1)

**Last Updated**: 2026-05-30
**Status**: 🟡 APPROVATO PARZIALMENTE — header bumped to v0.5.0; contenuto da rileggere contro la catena renderer-side.
**Maintainer**: subtask `css_builder/` (closed 2026-05-12).

CSS level 1 grammar. Covers rules, selectors, custom properties,
and the `@media` / `@supports` / `@import` at-rules.

## Purpose

Produce CSS stylesheets programmatically. Pairs with `CssRenderer`
for serialization. Supports the round-trip via
`CssBuilder.from_css(...)` (parse CSS source into builder code).

## Quick start

```python
from genro_builders.contrib.css import CssBuilderHandler


class Theme(CssBuilderHandler):
    def main(self, root):
        sheet = root.stylesheet()
        sheet.rule(color="red", padding="10px")\
             .selector(_class="card")\
             ._.selector(_class="panel")\
             ._.cssvar("primary", value="#3498db")


t = Theme(); t.create()
print(t.render())
```

Output:

```css
.card, .panel {
  color: red;
  padding: 10px;
  --primary: #3498db;
}
```

## Elements

| Element | Type | Sub-tags | Notes |
|---------|------|----------|-------|
| `stylesheet` | container | `rule[],importcss[]` | Top-level container. |
| `rule` | container | `selector[],cssvar[]` | A CSS rule. Property declarations go as kwargs. |
| `selector` | leaf | — | A selector clause (`.card`, `#main`, etc.). Multiple selectors under the same `rule` produce a selector list. |
| `selector_list` | container | `selector[]` | Explicit selector list (rarely needed; `rule` auto-builds it from its children). |
| `cssvar` | leaf | — | A CSS custom property declaration (`--name: value`). |
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
rule.selector(_class="card")
rule.selector(_class="panel")
rule.selector(_id="main")
```

This produces a selector list: `.card, .panel, #main { color: red; }`.

The `_class`, `_id`, `_attr` kwargs map to CSS selector syntax (a
class, an id, an attribute selector). Pseudo-classes and
combinators use the `pseudo=` and `combinator=` kwargs.

### Chaining with `._`

```python
sheet.rule(color="red")\
     .selector(_class="card")\
     ._.selector(_class="panel")\
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
`CssBuilderHandler` subclass whose `main(self, root)` rebuilds the
input.

## Render

`CssRenderer.render_css(built, render_target=None)`.

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
[../../src/genro_builders/contrib/css/examples/](../../src/genro_builders/contrib/css/examples/)
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
- Subtask handoff: `temp/subtask/css_builder/finaldoc.md` (internal).
