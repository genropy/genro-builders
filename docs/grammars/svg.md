# SVG grammar

**Last Updated**: 2026-05-18
**Status**: 🟡 APPROVATO PARZIALMENTE — allineato a v0.4.0, contenuto sostanziale da rileggere.
**Maintainer**: core team.

SVG 1.1 grammar. 56 elements covering shapes, paths, text,
gradients, filters.

## Purpose

Produce SVG markup for vector graphics: charts, icons, diagrams,
illustrations. Pairs with `SvgRenderer` for serialization (XML
self-closing tags with a space, e.g. `<rect />`, kebab-case
attribute names where required).

## Quick start

```python
from genro_builders.contrib.svg import SvgBuilderHandler


class Chart(SvgBuilderHandler):
    def main(self, root):
        svg = root.svg(viewBox="0 0 100 100")
        svg.rect(x=10, y=10, width=80, height=80, fill="red")
        svg.circle(cx=50, cy=50, r=20, fill="white")


c = Chart(); c.create()
print(c.render())
```

Output (single line, default mode):

```xml
<svg viewBox="0 0 100 100"><rect x="10" y="10" width="80" height="80" fill="red" /><circle cx="50" cy="50" r="20" fill="white" /></svg>
```

## Elements

56 elements declared in
[svg_elements.py](../../src/genro_builders/contrib/svg/svg_elements.py).
Grouped by purpose:

| Group | Examples |
|-------|----------|
| Root / container | `svg`, `g`, `defs`, `symbol`, `marker` |
| Shapes (leaf) | `rect`, `circle`, `ellipse`, `line`, `polyline`, `polygon`, `path` |
| Text | `text`, `tspan`, `textPath` |
| Gradients / patterns | `linearGradient`, `radialGradient`, `pattern`, `stop` |
| Filters | `filter`, `feGaussianBlur`, `feBlend`, `feColorMatrix`, ... |
| Animation | `animate`, `animateTransform`, `set` |
| References | `use`, `image`, `foreignObject` |

Most shapes are leaves (`sub_tags=""`). Containers use `*` as
sub-tags (any SVG child accepted).

## Common patterns

### Kebab-case attributes

SVG accepts attributes like `stroke-width`, `stroke-dasharray`,
`font-size`. Python kwargs use underscores; the renderer converts:

```python
svg.line(x1=0, y1=0, x2=100, y2=0,
         stroke="black", stroke_width=2, stroke_dasharray="5,5")
```

→ `<line x1="0" y1="0" x2="100" y2="0" stroke="black" stroke-width="2" stroke-dasharray="5,5" />`

### Chaining leaves with `._`

Most SVG content is leaves. Use `._` to keep the call stream
flowing:

```python
svg = root.svg(viewBox="0 0 100 100")
svg.rect(x=10, y=10, width=80, height=80, fill="red")\
   ._.rect(x=20, y=20, width=60, height=60, fill="blue")\
   ._.circle(cx=50, cy=50, r=10, fill="white")
```

See [../builders/patterns.md](../builders/patterns.md).

### viewBox and coordinate space

The renderer does not validate `viewBox` — pass it as a string.
Coordinates inside the SVG can be ints, floats, or strings; they
serialize unchanged.

## Render

`SvgRenderer.render_svg(built, render_target=None)`.

The only mode is `svg`. Void tags emit with a space before the
close (`<rect />`), in line with SVG convention. Pretty printing is
not yet implemented.

## Validation rules

- The root must be `<svg>` (or, when used as a sub-builder, the
  `<svg>` of the host HTML page).
- `<tspan>` and `<textPath>` only valid under `<text>`.
- `<stop>` only valid under gradients.
- Container elements accept any SVG child (`sub_tags="*"`); the
  schema does not enforce semantic constraints (e.g. "filters
  inside `<defs>`").

Validation errors raise `ValueError` at `create()` time.

## Worked examples

Examples under
[../../src/genro_builders/contrib/svg/examples/](../../src/genro_builders/contrib/svg/examples/):

- `01_introduction/` — three-view (`.py`, `.ipynb`, `.svg`).
- Plus legacy single-view examples (`badge_sheet/`, `bar_chart/`,
  `card_shadow/`, `concentric_circles/`, `house_icon/`) that
  predate the three-view format.

## Known limitations

- Pretty printing is not implemented for SVG. `pretty=True` is
  ignored.
- `@subbuilder(SvgBuilder)` from HTML is declared but not yet
  active (see `temp/subtask/subbuilder/`).
- No automatic xmlns declarations. The user adds
  `xmlns="http://www.w3.org/2000/svg"` on the root `<svg>` if the
  output is consumed standalone.
- Animation (`<animate>` and friends) is in the schema but the
  renderer does not specialize for the SMIL syntax — attributes
  pass through verbatim.

## References

- Source: `src/genro_builders/contrib/svg/`.
- Renderer: `src/genro_builders/contrib/svg/svg_renderer.py`.
- Schema: `src/genro_builders/contrib/svg/svg_elements.py`.
- Contract: `roadmap/architecture-contract.md`.
