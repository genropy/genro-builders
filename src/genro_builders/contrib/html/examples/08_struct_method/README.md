# 08 — Struct methods: reusable blocks

A `@struct_method` is a named block of build logic you can call from any
node, like a macro. It is the simplest way to factor out repeated markup
without leaving the handler.

> Run it: `python 08_struct_method.py` (writes the `.html`).

## Defining and calling

Decorate a handler method with `@struct_method`. The first argument
after `self` (by convention `pane`) is the node it was called from:

```python
@struct_method
def card(self, pane, title, body, color="#3498db"):
    box = pane.div(class_="card", border_top=f"3px solid {color}")
    box.h3(title)
    box.p(body)
```

Call it on any node; extra args/kwargs are forwarded:

```python
body.card("Designer", "Alice", color="#e74c3c")
body.card("Engineer", "Bob", color="#2ecc71")
body.card("Manager", "Carol")
```

Three calls, one definition. The block builds straight into `pane` — no
return value is needed (you may return a node to chain if you like).

## Dispatch name: prefix strip + case-insensitive

The dispatch name is the method name with the part before the first
underscore stripped, and lookup is case-insensitive:

```python
@struct_method
def ui_badge(self, pane, text):
    pane.span(text, class_="badge")

body.badge("...")   # 'ui_' stripped -> dispatch name 'badge'
body.Badge("...")   # same block (case-insensitive)
```

An explicit name is also possible: `@struct_method("alias")`.

## struct_method vs component

Both factor out reusable structure, but they differ:

| | `@struct_method` | `@component` (see 09) |
|---|---|---|
| lives on | the handler | a mixin, mounted via `pyrequires` |
| is grammar? | no — a dispatched call | yes — a word of the grammar |
| receives | the calling node (`pane`) | a fresh `root` to populate |
| expands | immediately, at call | at render time |

Reach for `@struct_method` for quick local reuse; for a reusable,
grammar-level, data-driven block, see the component example.

## Takeaways

- `@struct_method` defines a callable block; `pane` is the node it was
  called from; args/kwargs are forwarded.
- The dispatch name strips the prefix before the first underscore and is
  case-insensitive; an explicit name is allowed.
- It builds in place — no grammar entry, no render-time expansion.
