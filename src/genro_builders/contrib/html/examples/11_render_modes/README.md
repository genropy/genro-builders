# 11 — Render modes

The document you build is a data tree, independent of how it is
serialized. A **render mode** picks the serializer. The same `Page`
renders to HTML, XML or YAML by changing one argument.

> Run it: `python 11_render_modes.py` (writes `11_render_modes.txt`).

## Choosing a mode

`render(mode=..., pretty=..., target=False)` selects the output. Each
builder exposes a `renderer_<mode>` property; the handler resolves the
mode argument to it.

```python
page.render()                         # default mode (html), compact
page.render(pretty=True)              # html, indented
page.render(mode="xml", pretty=True)  # xml
page.render(mode="yaml")              # yaml
```

`target=False` forces the result to be returned as a string (instead of
written to a registered target).

## What differs between modes

**html** — the HTML dialect's renderer. CSS-aware: `color="#333"`
becomes an inline `style`; void tags follow HTML idioms.

```
<p style="color: #333">Some text</p>
```

**xml** — the universal renderer, available on every builder via
`renderer_xml`. No HTML-specific rules: attributes stay attributes.

```
<p color="#333">Some text</p>
```

**yaml** — a structural view of the tree (`renderer_yaml`). Useful for
inspection and data interchange. PyYAML is an optional dependency (extra
`[yaml]`); the renderer raises a clear error if it is absent.

```
body:
  div:
    class: card
    h3: Title
    p: Some text
```

## `pretty`

`pretty=True` indents nested elements (two spaces per level) for HTML and
XML; the default is compact single-line output. Pick compact for the
wire, pretty for reading.

## Takeaways

- The built tree is mode-agnostic; the renderer decides the bytes.
- `mode="html"|"xml"|"yaml"` selects the serializer; each is a
  `renderer_<mode>` on the builder.
- `html` applies dialect rules (CSS, void tags); `xml` is the neutral
  universal walk; `yaml` is a structural view.
- `pretty` toggles indentation; `target=False` returns the string.
