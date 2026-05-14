# Common patterns

**Version**: 0.1.0
**Last Updated**: 2026-05-14
**Status**: 🔴 DA REVISIONARE — Documento non ancora approvato.

Cross-grammar idioms. These work the same way on HTML, SVG, CSS, or
any user-defined dialect built on `BagBuilderBase`.

## `._` chaining — climbing back to the parent

Every node exposes a `_` attribute that returns the parent bag.
This makes leaf elements (`<img>`, `<rect>`, `<br>`, `selector`,
`cssvar`) easy to chain without breaking the call stream.

Every element call returns the newly created node. For leaves the
node has no children, so chaining a sibling would otherwise require
a fresh variable. `._` solves this without changing the return
contract — leaves still return themselves, and the user explicitly
asks to step back up.

### SVG

```python
from genro_builders.contrib.svg import SvgBuilderHandler

class Chart(SvgBuilderHandler):
    def main(self, root):
        svg = root.svg(viewBox="0 0 100 100")
        svg.rect(x=10, y=10, width=80, height=80, fill="red")\
           ._.rect(x=20, y=20, width=60, height=60, fill="blue")\
           ._.circle(cx=50, cy=50, r=10, fill="white")
```

Output:

```xml
<svg viewBox="0 0 100 100">
  <rect x="10" y="10" width="80" height="80" fill="red" />
  <rect x="20" y="20" width="60" height="60" fill="blue" />
  <circle cx="50" cy="50" r="10" fill="white" />
</svg>
```

### CSS

```python
from genro_builders.contrib.css import CssBuilderHandler

class Theme(CssBuilderHandler):
    def main(self, root):
        sheet = root.stylesheet()
        sheet.rule(color="red")\
             .selector(_class="card")\
             ._.selector(_class="panel")\
             ._.cssvar("primary", value="#3498db")
```

Output:

```css
.card, .panel {
  color: red;
  --primary: #3498db;
}
```

### When `._` is not needed

For non-leaf elements that accept children, chain children directly
on them:

```python
body = root.body()
body.h1("Title")
body.p("First paragraph")
body.p("Second paragraph")
```

Use `._` only when a leaf node interrupts the chain.

## Render targets — where the output goes

By default `handler.render()` returns the rendered string.
Alternatively, set `handler.render_target` to redirect:

```python
# Return a string (default)
text = page.render()

# Write to a file
with open("out.html", "w") as f:
    page.render_target = f
    page.render()

# Pipe through a callable
page.render_target = lambda chunk: socket.send(chunk)
page.render()
```

A render target may be:

- `None` — the renderer accumulates a string and returns it.
- An object with a `.write(text)` method — file, stream, socket.
- A callable — invoked once with the full text.

Any other type raises `TypeError`.

## `node_id` and lookup

Assign a stable identifier to a node to retrieve it later:

```python
class Page(HtmlBuilderHandler):
    def main(self, root):
        root.body().h1("Title", node_id="header")

page = Page(); page.create(); page.build()

# Find it on source or built side:
source_h1 = page.node_by_id("header", stage="source")
built_h1  = page.node_by_id("header", stage="built")
```

`node_id` is unique per handler. Collisions raise `ValueError`
during `create()`.

The `node_by_id` index is used internally to resolve symbolic
pointers (`^#node_id.field`) once the data layer ships. See
`roadmap/data-architecture.md` §10.

## Render modes

A grammar's renderer can expose multiple `render_<mode>` methods.
The handler dispatches via `mode`:

```python
print(page.render())              # default mode (defined by builder)
print(page.render(mode="xml"))    # XML mode (Bag.to_xml under the hood)
print(page.render(mode="html"))   # HTML mode (HtmlRenderer.render_html)
print(page.render(pretty=True))   # mode-specific kwarg
```

Mode-specific kwargs are filtered against the method's signature:
unknown kwargs are silently ignored. This lets the same call site
work across grammars with different kwarg sets.
