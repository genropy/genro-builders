# 12 — A component collection

`DemoComponents` is the didactic mini collection: how to package
`@component` pieces in a mixin and use them as grammar. It is NOT the
product widget kit — the effective collections (typed input widgets,
`labeled_field`, client bindings) live in **genro-ws-web**.

```python
class Page(HtmlBuilder, DemoComponents):
    def main(self, root):
        root.labeledInput(label="Name", value="^.name")
        root.swatch(color="^.color")
```

## The closed citizen (CMP.1)

A `@component` is CLOSED: the caller parameterizes it, never fills it.
The name in the source is the cross-runtime contract — the node says
`labeledInput`, the expansion is ephemeral at render time.

## Reading AND writing (CMP.4)

A reactive `value` pointer **passes through** to the inner `<input>`:
in the reactive render the element carries both the resolved value and
its write-back address —

```html
<input value="Mario Rossi" data-value-pointer="main.person.name"/>
```

— so the piece displays, re-renders when the datum changes (the
component node is the registered reader, CMP.7), and a client knows
where to write back. `swatch` shows the read-only half: a pointer in a
plain attribute (`background`).

Extra attrs reach the inner input untouched (`placeholder="..."`).

Fillable containers are the OTHER citizen (`@container`, CMP.9):
example 13.

Run it from this folder:

```bash
python component_collection.py
```
