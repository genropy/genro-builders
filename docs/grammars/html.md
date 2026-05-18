# HTML grammar

**Version**: 0.1.0
**Last Updated**: 2026-05-14
**Status**: 🔴 DA REVISIONARE — Documento non ancora approvato.
**Maintainer**: core team.

HTML5 grammar generated from the W3C schema. 112 elements, full
parent/child validation.

## Purpose

Produce HTML5 markup. Supports both XHTML-style self-closing void
tags (`<img/>`) and bare HTML5 (`<img>`), with optional pretty
printing. Pairs with `HtmlRenderer` for serialization. Pairs with
the CSS-kwarg machinery for inline styling.

## Quick start

```python
from genro_builders.contrib.html import HtmlBuilderHandler


class Page(HtmlBuilderHandler):
    def main(self, root):
        root.html().head().title("Hello")
        body = root.html().body()
        body.h1("Hello")
        body.p("genro-builders")


p = Page(); p.create()
print(p.render(pretty=True))
```

## Elements

The grammar is auto-generated from the W3C HTML5 Validator schema
([html5_elements.py](../../src/genro_builders/contrib/html/html5_elements.py),
**do not edit manually**). It contains 112 tags grouped by content
category (flow content, phrasing content, etc.) plus their parent
and sub-tag constraints.

Highlights:

- All 16 HTML5 **void elements** are present as leaves:
  `area`, `base`, `br`, `col`, `embed`, `hr`, `img`, `input`,
  `link`, `meta`, `param`, `source`, `track`, `wbr`, `command`,
  `keygen`.
- Container elements use the W3C content categories.
- A subset of phrasing elements is exposed under abstracts like
  `@phrasing`, `@flow`, `@interactive`.

Refer to the auto-generated module for the exhaustive list.

## Common patterns

### Attributes with reserved Python keywords

Some HTML attribute names collide with Python keywords (`class`,
`for`). The grammar uses an underscore prefix to disambiguate:

```python
body.div(_class="card")
body.label(_for="email")
```

The renderer strips the leading underscore on output.

### Inline CSS via kwargs

`HtmlRenderer` recognizes 24 CSS root names as kwargs and emits
them in a `style="..."` attribute. Sub-properties use underscore
syntax:

```python
body.div(
    "content",
    id="main", _class="card",
    color="red",
    background="#fff",
    padding="12px",
    padding_top=10,
    font_size="14px",
    text_align="center",
    rounded=12,
    transform_rotate=-3,
    style="margin: 4px",
)
```

`style_<prop>` is the escape hatch for CSS properties outside the
curated 24:

```python
body.div(style_aspect_ratio="16 / 9")
```

For the full kwarg / macro reference see
[../builders/patterns.md](../builders/patterns.md) and the
renderer source.

### Chaining leaves with `._`

```python
body.h1("Title")\
   ._.p("paragraph one")\
   ._.p("paragraph two")
```

See [../builders/patterns.md](../builders/patterns.md).

## Render

`HtmlRenderer.render_html(built, render_target=None, *, xml=True,
pretty=False)`.

| Kwarg | Default | Effect |
|-------|---------|--------|
| `xml` | `True` | Void tags as `<img/>` (XHTML). `False` → `<img>` (HTML5). |
| `pretty` | `False` | Two-space indentation and trailing newline per node. |

`render_xml` (inherited from `RendererBase`) is also available; it
delegates to `Bag.to_xml(pretty=...)` and produces stable XML.

## Validation rules

- `<rect>`, `<circle>`, `<path>` and other SVG tags are **not**
  valid here. The grammar rejects them unless they appear inside a
  `@subbuilder(SvgBuilder)` boundary (see `<svg>`).
- `<li>` must appear inside `<ul>` or `<ol>`.
- `<head>` elements (title, meta, link, ...) reject body content.
- Void tags reject children.

Validation errors raise `ValueError` at `create()` time.

## Worked examples

Two ready-to-run examples live under
[../../src/genro_builders/contrib/html/examples/](../../src/genro_builders/contrib/html/examples/):

- `01_introduction/` — minimal page (three-view: `.py`, `.ipynb`,
  `.html`).
- `02_inline_styling/` — CSS kwarg machinery, macros, escape
  syntax.

## Known limitations

- `<svg>` as a sub-builder boundary is declared in the schema but
  not yet active (see `temp/subtask/subbuilder/`).
- The grammar covers HTML5 but not yet HTML5 templates,
  custom-element semantics, or shadow DOM.
- No automatic doctype prepend. The user adds `<!DOCTYPE html>` by
  hand when needed.
- HTML5-specific accessibility hints (`aria-*` attributes) are
  not validated — they pass through as opaque kwargs.

## References

- Source: `src/genro_builders/contrib/html/`.
- Renderer: `src/genro_builders/contrib/html/html_renderer.py`.
- Schema (generated): `src/genro_builders/contrib/html/html5_elements.py`.
- Contract: `roadmap/architecture-contract.md`.
