# SvgBuilder

SVG document builder with 60+ elements: shapes, text, gradients, filters,
animation, clipping/masking, and descriptive elements.

## Install

```bash
pip install genro-builders
```

## Quick start

```python
from genro_builders.contrib.svg import SvgBuilder

builder = SvgBuilder()
svg = builder.source.svg(width="200", height="200", viewBox="0 0 200 200")
svg.rect(x="10", y="10", width="80", height="80", fill="steelblue")
svg.circle(cx="150", cy="50", r="40", fill="coral")

builder.build()
print(builder.render())
```

## Attribute naming

SVG uses kebab-case (`stroke-width`) — use underscores in Python,
the renderer converts them automatically:

```python
svg.rect(stroke_width="2", fill_opacity="0.5")
# renders as: stroke-width="2" fill-opacity="0.5"
```

## Examples

See [examples/](examples/) for complete working examples:

- **svg_chart_example.py** — Bar chart, concentric circles, house icon, card with drop shadow

## Documentation

Full documentation: [docs/builders/svg-builder.md](../../../../docs/builders/svg-builder.md)
