# 00 — Hello world, reactive

The same page as `no_data/00_hello_world`, but now the source is **mutated
at runtime** inside live sections, and each mutation re-renders the document.

## The Application

Reactivity lives above the handler: an **Application** owns the handler and
makes it reactive (it sets itself as the handler's `application`). The shared
`ExampleApp` mounts a page, renders once, and exposes `live()`:

```python
class ExampleApp:
    def __init__(self, page, target):
        self.handler = BuilderHandler()
        self.handler.application = self      # makes the handler reactive
        self.handler.add_builder(main=page)
        self.page = page
        page.set_render_target(target)
        page.create()
        page.render(pretty=True)             # first render: startup
```

A page that only renders once needs no handler; a page that reacts to source
mutations needs a handler **with an application**.

## One change per live section

`CustomApp` subclasses `ExampleApp` and declares one numbered
`change_NN_*(self, source)` method per mutation. `run()` executes each inside
its own `with self.live():` and prints the document after the section closes —
that is when the re-render happens:

```python
class CustomApp(ExampleApp):
    def change_00_add_one_div(self, source):
        source["body"].div("one div")
    ...
```

The body is reached by its **stable label** (`source["body"]`): `body` is a
singleton element, so it keeps the label `body` instead of an auto-generated
one — no `node_id` needed.

## The mutations

Source mutations go through the grammar / canonical Bag API:

- **add a child**: `source["body"].div("text")`
- **remove a child**: `source["body"].del_item("div_0")`
- **insert at a position**: `source["body"].div("x", node_position=4)`
- **set an existing node** (same `node_label`): `div("new", node_label="div_0")`
  updates the value instead of inserting a new node;
- **set only attributes**: `div(node_label="div_0", class_="hot")` sets the
  attribute and resets the value to `None` (no value passed).

## Injecting a prepared block

A subtree can be built offline with `new_root()` and attached live:

- **wrapped**: `source["body"].div(block)` — the block becomes the content of
  a new `<div>` wrapper;
- **merged**: `source["body"].update(block)` — the block's nodes are merged
  straight into the body and `update()` fires an `ins` per node (reactive).
  CAVEAT: `update()` merges **by label** — a block node whose label already
  exists in the body overwrites the existing one.

## Run

```bash
python -m genro_builders.contrib.html.examples.reactive.00_hello_world.hello_world
```

Each section prints the document after its mutation. The sections run in
sequence on the **same** document, so the state accumulates — a real reactive
flow.
