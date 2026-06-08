# 04 — Data-elements at create time

Data-elements compute the *data* a page shows. There are three, and they
all run during `create()` — **before** any reactivity is armed — so a
plain `render()` already reflects their results. No `live()` section is
needed here; reacting to later changes is a separate topic.

> Run it: `python 04_data_elements.py` (writes `04_data_elements.html`).

## The data scope: `datapath`

A container opens a data scope with `datapath`:

```python
body = root.body(datapath="invoice")
```

From there on, a child's `^.name` pointer resolves against that scope —
`^.amount` means `invoice.amount`. The leading `.` in a data-element
destination (`.amount`) is the same relative form.

## The three data-elements

| Element | Signature | Runs at create? | Role |
|---|---|---|---|
| `data_setter` | `data_setter(".path", value)` | **always** | seed a datum |
| `data_formula` | `data_formula(".path", "func", arg="^.x", _on_start=True)` | only if `_on_start=True` | pure derived value |
| `data_controller` | `data_controller("func", arg="^.x", _on_start=True)` | only if `_on_start=True` | side-effect step |

`func` is resolved **by name**. The simplest source is a `@staticmethod`
on the handler itself.

They are **transparent**: a data-element emits no markup. Only the
`^.path` pointers that *read* its result show up in the HTML.

## Section 1 — `data_setter`

```python
body.data_setter(".amount", 1000)
body.data_setter(".currency", "EUR")
body.p("Amount: ").span("^.amount")
```

A setter always runs at create, so `invoice.amount` is in `self.data`
ready for the first render. The `<span>` reads it back. → `1000`, `EUR`.

## Section 2 — `data_formula` with `_on_start`

```python
@staticmethod
def calc_vat_total(net, rate):
    return round(net * (1 + rate), 2)

body.data_formula(
    ".total", "calc_vat_total", net="^.net", rate="^.rate",
    _on_start=True,
)
```

A formula is **pure**: `func(**bindings) -> destination`. The bindings
are pointers (`net="^.net"`) resolved before the call. With
`_on_start=True` it runs once at create, so the static render shows the
gross figure. → `1220.0`.

## Section 3 — `data_controller` with `_on_start`

```python
@staticmethod
def build_label(node, count):
    word = "item" if count == 1 else "items"
    node.set_relative_data(".label", f"{count} {word}")

body.data_controller("build_label", count="^.count", _on_start=True)
```

A controller is a **side-effect** step. Unlike a formula it receives the
`node` first and writes the bag itself (`node.set_relative_data`), so it
can target any path — not just one destination. → `3 items`.

## Section 4 — a dormant formula

The same formula as Section 2 but **without** `_on_start`:

```python
body.data_formula(".total", "calc_vat_total", net="^.net", rate="^.rate")
```

It does not run at create: `invoice.total` is never written, so `^.total`
renders empty. The formula would still fire later — inside a `live()`
section, when `net` or `rate` change. That reactive behaviour is covered
elsewhere.

## Takeaways

- `data_setter` seeds and **always** runs at create.
- `data_formula` / `data_controller` run at create **only** with
  `_on_start=True`; otherwise they wait for a reactive change.
- A formula returns one value to one destination; a controller gets the
  node and writes the bag freely.
- Data-elements never emit markup — pointers read their results.
