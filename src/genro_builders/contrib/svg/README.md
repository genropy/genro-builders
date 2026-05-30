# SvgBuilder

SVG document builder with 60+ elements: shapes, text, gradients,
filters, animation, clipping/masking, and descriptive elements.

## Install

```bash
pip install genro-builders
```

## Quick start

```python
from genro_builders.contrib.svg import SvgBuilderHandler


class Card(SvgBuilderHandler):
    def main(self, root):
        svg = root.svg(width=200, height=200, viewBox="0 0 200 200")
        svg.rect(x=10, y=10, width=80, height=80, fill="steelblue")
        svg.circle(cx=150, cy=50, r=40, fill="coral")


page = Card()
page.create()
print(page.render())
```

## Attribute naming

SVG uses kebab-case (`stroke-width`) — use underscores in Python,
the renderer converts them automatically:

```python
svg.rect(stroke_width=2, fill_opacity=0.5)
# renders as: stroke-width="2" fill-opacity="0.5"
```

## HTML inside SVG

Sub-builder polymorphism: a `<svg>` tree can host HTML via
`svg.html(...)`. The renderer wraps the HTML subtree in
`<foreignObject xmlns="http://www.w3.org/1999/xhtml">` automatically,
so the SVG remains well-formed.

```python
class Badge(SvgBuilderHandler):
    def main(self, root):
        svg = root.svg(viewBox="0 0 200 80", width=200, height=80)
        svg.rect(x=0, y=0, width=200, height=80, fill="#2c3e50")
        fo = svg.html(x=20, y=20, width=160, height=40)
        fo.div("Mixed content", style="color: white")
```

## Examples

See [examples/](examples/) — runnable tutorials, each shipped as
`.py` + `.ipynb` + rendered `.html`:

- **01_introduction** — minimal SVG document
- **bar_chart** — basic chart with `rect`, `text`
- **concentric_circles** — circle composition
- **house_icon** — shape composition
- **card_shadow** — filter usage
- **badge_sheet** — multi-document layout

## Documentation

Full documentation: [docs/grammars/svg.md](../../../../docs/grammars/svg.md)
