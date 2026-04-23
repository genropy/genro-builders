# SvgBuilder

The `SvgBuilder` provides SVG support with 60+ elements covering shapes,
text, gradients, filters, animation, clipping, and descriptive elements.

`SvgBuilder` is a **contributed builder** — it lives in `genro_builders.contrib`
and is not loaded unless explicitly imported. It depends on the core framework
(`BagBuilderBase`, `@element`, `BagRendererBase`) but adds no external dependencies.

## Basic Usage

```python
from genro_builders.contrib.svg import SvgBuilder

builder = SvgBuilder()
svg = builder.source.svg(width="200", height="200", viewBox="0 0 200 200")
svg.rect(x="10", y="10", width="80", height="80", fill="steelblue")
svg.circle(cx="150", cy="50", r="40", fill="coral")

builder.build()
print(builder.render())
```

Output:

```xml
<svg width="200" height="200" viewBox="0 0 200 200">
  <rect x="10" y="10" width="80" height="80" fill="steelblue" />
  <circle cx="150" cy="50" r="40" fill="coral" />
</svg>
```

## Attribute Naming

SVG uses kebab-case (`stroke-width`, `fill-opacity`) but Python requires
identifiers. Use underscores — the renderer converts them automatically
for known presentation attributes:

```python
svg.rect(width="50", height="50",
         stroke_width="2",        # -> stroke-width
         fill_opacity="0.5",      # -> fill-opacity
         stroke_dasharray="5,3",  # -> stroke-dasharray
)
```

The full list of converted attributes includes `stroke_width`, `fill_opacity`,
`fill_rule`, `stroke_linecap`, `stroke_linejoin`, `font_size`, `font_family`,
`font_weight`, `text_anchor`, `text_decoration`, `stop_color`, `stop_opacity`,
`clip_path`, `clip_rule`, `marker_end`, `marker_start`, `paint_order`, and more.

Use `class_` for the CSS `class` attribute (same convention as HTML).

## Self-Closing Tags

Void elements (shapes, stops, filter primitives) render as self-closing:

```xml
<circle cx="50" cy="50" r="40" />
<rect x="0" y="0" width="100" height="100" />
<stop offset="0%" stop-color="red" />
```

Container elements (`svg`, `g`, `defs`, `text`, `filter`, etc.) use open/close tags.

## Shapes

All SVG shape primitives are available:

```python
builder = SvgBuilder()
svg = builder.source.svg(width="300", height="200")

svg.rect(x="10", y="10", width="80", height="60", rx="5", fill="#3498db")
svg.circle(cx="150", cy="40", r="30", fill="#e74c3c")
svg.ellipse(cx="250", cy="40", rx="40", ry="25", fill="#2ecc71")
svg.line(x1="10", y1="100", x2="290", y2="100", stroke="#999", stroke_width="1")
svg.polyline(points="10,180 60,120 110,160 160,110 210,150", fill="none", stroke="#333")
svg.polygon(points="250,110 290,180 210,180", fill="#f39c12")
svg.path(d="M10,200 Q80,120 150,200", fill="none", stroke="#8e44ad", stroke_width="2")
```

## Text

```python
svg = builder.source.svg(width="200", height="100")

# Simple text
svg.text("Hello SVG", x="100", y="50", text_anchor="middle", font_size="24")

# Text with styled spans
t = svg.text("Normal ", x="10", y="80", font_size="14")
t.tspan("Bold", font_weight="bold")
```

## Gradients and Patterns

Define gradients inside `<defs>`, then reference via `fill="url(#id)"`:

```python
svg = builder.source.svg(width="200", height="200")

# Define gradient
defs = svg.defs()
grad = defs.linearGradient(id="sunset", x1="0", y1="0", x2="0", y2="1")
grad.stop(offset="0%", stop_color="#ff6b6b")
grad.stop(offset="100%", stop_color="#ffd93d")

# Use gradient
svg.rect(width="200", height="200", fill="url(#sunset)")
```

Radial gradients work the same way:

```python
rg = defs.radialGradient(id="spotlight", cx="50%", cy="50%", r="50%")
rg.stop(offset="0%", stop_color="white")
rg.stop(offset="100%", stop_color="transparent")
```

## Filters

SVG filters are defined in `<defs>` and applied via the `filter` attribute:

```python
svg = builder.source.svg(width="200", height="160")

defs = svg.defs()
f = defs.filter(id="shadow", x="-20%", y="-20%", width="140%", height="140%")
f.feGaussianBlur(stdDeviation="4", result="blur")
f.feOffset(dx="4", dy="4", result="offsetBlur")
merge = f.feMerge()
merge.feMergeNode(in_="offsetBlur")
merge.feMergeNode(in_="SourceGraphic")

# Card with shadow
svg.rect(x="30", y="20", width="140", height="100", rx="8",
         fill="white", stroke="#ddd", filter="url(#shadow)")
```

Available filter primitives: `feGaussianBlur`, `feOffset`, `feBlend`,
`feColorMatrix`, `feComposite`, `feFlood`, `feMerge`, `feMergeNode`,
`feDropShadow`, `feDiffuseLighting`, `feSpecularLighting`, `fePointLight`,
`feDistantLight`, `feSpotLight`, `feMorphology`, `feTurbulence`,
`feDisplacementMap`, `feConvolveMatrix`, `feImage`, `feTile`.

## Groups and Transforms

Use `<g>` to group elements and apply shared transforms or styles:

```python
svg = builder.source.svg(width="200", height="200")

g = svg.g(transform="translate(50, 50) rotate(45)")
g.rect(width="40", height="40", fill="coral")
g.rect(x="50", width="40", height="40", fill="steelblue")
```

## Symbols and Reuse

Define reusable symbols in `<defs>`, render them with `<use>`:

```python
svg = builder.source.svg(width="300", height="100")

defs = svg.defs()
sym = defs.symbol(id="star", viewBox="0 0 24 24")
sym.path(d="M12 2l3.09 6.26L22 9.27l-5 4.87L18.18 22 12 18.27 5.82 22 7 14.14 2 9.27l6.91-1.01L12 2z")

# Render the symbol at different positions and sizes
svg.use(href="#star", x="10", y="20", width="30", height="30", fill="gold")
svg.use(href="#star", x="60", y="10", width="50", height="50", fill="coral")
svg.use(href="#star", x="130", y="25", width="25", height="25", fill="steelblue")
```

## Clipping and Masking

```python
svg = builder.source.svg(width="200", height="200")

defs = svg.defs()
clip = defs.clipPath(id="circle-clip")
clip.circle(cx="100", cy="100", r="80")

# Image clipped to circle shape
svg.image(href="photo.jpg", width="200", height="200", clip_path="url(#circle-clip)")
```

## Animation

```python
svg = builder.source.svg(width="200", height="100")

c = svg.circle(cx="20", cy="50", r="15", fill="coral")
c.animate(attributeName="cx", from_="20", to="180", dur="2s", repeatCount="indefinite")
```

## Reactive Data Binding

SvgBuilder works with the full reactive infrastructure:

```python
builder = SvgBuilder()
builder.data["radius"] = "40"
builder.data["color"] = "steelblue"

svg = builder.source.svg(width="200", height="200")
svg.circle(cx="100", cy="100", r="^radius", fill="^color")

builder.build()
builder.subscribe()
print(builder.output)

# Change data -> automatic re-render
builder.data["color"] = "coral"
print(builder.output)
```

## Element Reference

### Structural

`svg`, `g`, `defs`, `symbol`, `use`

### Shapes (leaf)

`rect`, `circle`, `ellipse`, `line`, `polyline`, `polygon`, `path`, `image`

### Text

`text` (container: `tspan`, `textPath`), `tspan`, `textPath`

### Gradients

`linearGradient`, `radialGradient` (container: `stop`), `stop`, `pattern`

### Clipping / Masking

`clipPath`, `mask`, `marker`

### Filters

`filter` (container), `feGaussianBlur`, `feOffset`, `feBlend`, `feColorMatrix`,
`feComposite`, `feFlood`, `feMerge` (container: `feMergeNode`), `feMergeNode`,
`feDropShadow`, `feDiffuseLighting`, `feSpecularLighting`, `fePointLight`,
`feDistantLight`, `feSpotLight`, `feMorphology`, `feTurbulence`,
`feDisplacementMap`, `feConvolveMatrix`, `feImage`, `feTile`

### Animation

`animate`, `animateTransform`, `animateMotion`, `set`

### Descriptive

`title`, `desc`, `metadata`

### Linking

`a`, `foreignObject`, `switch`
