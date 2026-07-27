# Common patterns

**Last Updated**: 2026-07-27
**Status**: 🟢 APPROVATO — allineato al contratto v0.9.0.

Cross-grammar idioms. These work the same way on HTML, SVG, CSS, or
any user-defined dialect built on `BuilderBase`.

## `._` chaining — climbing back to the parent

Every node exposes a `_` attribute that returns the parent bag.
This makes leaf elements (`<img>`, `<rect>`, `<br>`, `cssvar`) easy
to chain without breaking the call stream.

Every element call returns the newly created node. For leaves the
node has no children, so chaining a sibling would otherwise require
a fresh variable. `._` solves this without changing the return
contract — leaves still return themselves, and the user explicitly
asks to step back up.

### SVG

```python
from genro_builders.contrib.svg import SvgBuilder

class Chart(SvgBuilder):
    def main(self, root):
        svg = root.svg(viewBox="0 0 100 100")
        svg.rect(x=10, y=10, width=80, height=80, fill="red")\
           ._.rect(x=20, y=20, width=60, height=60, fill="blue")\
           ._.circle(cx=50, cy=50, r=10, fill="white")
```

Output (wrapped here for readability; the default render is one line):

```xml
<svg viewBox="0 0 100 100"><rect x="10" y="10" width="80" height="80" fill="red" />
<rect x="20" y="20" width="60" height="60" fill="blue" />
<circle cx="50" cy="50" r="10" fill="white" /></svg>
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

By default `page.render()` returns the rendered string. You can also
pass a target inline, or register one in advance.

### Inline target

```python
# Return a string (default)
text = page.render()

# Write to a file (this call only)
with open("out.html", "w") as f:
    page.render(target=f)

# Pipe through a callable (this call only)
page.render(target=lambda chunk: socket.send(chunk))
```

### Registered targets, one per mode

For repeated rendering, register a target once and let `render()`
find it. `set_render_target(target, mode=None)` registers under the
dialect's default mode unless `mode` says otherwise:

```python
page.set_render_target("out.html")              # default mode (html)
page.set_render_target("snapshot.xml", "xml")   # xml view

page.render()              # default mode, writes out.html
page.render(mode="xml")    # writes snapshot.xml
page.render(target=False)  # default mode, returns the string
print(page.rendered_target)  # read back the file just written
```

### Target semantics

Inside `render(target=...)`:

- `False` — forces return-as-string, **ignoring** any registered
  target for the chosen mode;
- any other falsy value (`None`, `""`, `0`) — falls back to the
  target registered under the mode;
- truthy value — used directly as the target for this call only.

A render target may be:

- `None` — the renderer accumulates a string and returns it.
- A path string — opened for writing.
- An object with a `.write(text)` method — file, stream, socket.
- A callable — invoked with the rendered output.

The renderer rejects any other type with `TypeError`.

## `node_id` and lookup

Assign a stable identifier to a node to retrieve it later:

```python
from genro_builders.contrib.html import HtmlBuilder

class Page(HtmlBuilder):
    def main(self, root):
        root.body().h1("Title", node_id="header")

page = Page(); page.create()

source_h1 = page.node_by_id("header")
```

`node_id` is unique **per builder**. Collisions raise during
`create()`.

The `node_by_id` lookup walks the source bag and stops at the first
match. It is used internally to resolve symbolic pointers
(`^#node_id.field`); see `roadmap/data-architecture.md` §10.

## Render modes

A builder declares the modes it supports by exposing
`renderer_<mode>` properties (e.g. `renderer_html` on `HtmlBuilder`;
`renderer_xml` and `renderer_yaml` on `BuilderBase`, so every dialect
can serve those views). `render` dispatches via `mode`:

```python
print(page.render())              # dialect's default mode
print(page.render(mode="xml"))    # XML view
print(page.render(pretty=True))   # mode-specific kwarg
```

Mode-specific kwargs are passed verbatim through the walk to the
dialect's `rendered_item(node, item, runtime_attrs, **opts)`;
unknown kwargs are tolerated and propagated to children (each
dialect picks the ones it understands).
