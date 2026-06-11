# 13 — A container collection

`DemoContainers` is the didactic mini collection for the OTHER citizen
(`@container`, CMP.9): pieces that generate REAL source nodes at call
time, which the CALLER fills. It is NOT the product kit — the
effective containers (border/tab, with data-driven switching and
iframe-safe morphs) live in **genro-ws-web**.

```python
class Page(HtmlBuilder, DemoContainers):
    def main(self, root):
        people = root.card(title="People")
        people.p("Anna, Marco, Sara")
```

## Fillability is the discriminant

A `@component` is closed: parameterized, never filled. A `@container`
is the opposite: the call builds the piece's own nodes NOW (here the
card's title bar and body) and returns a pane — what goes inside is
the caller's business, with the full grammar available.

Real nodes mean real identity (`target_id`): every part of the card is
individually patchable in the reactive render.

The container method runs at CALL time on the real source (no
ephemeral expansion): what it builds is ordinary source, what it
returns is an ordinary node.

Run it from this folder:

```bash
python container_collection.py
```
