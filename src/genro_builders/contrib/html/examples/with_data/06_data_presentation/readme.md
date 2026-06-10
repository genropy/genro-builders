# 06 — Data presentation

The datum knows how to present itself: presentation metadata lives on
the **data node**, and every element reading the datum renders it
accordingly — reactively, because the attributes survive value updates.

## `mask` — how the value is written

```python
data.set_item("temperature", 39.2, mask="%s°")
```

`mask` wraps the rendered value; `%s` is the value (the legacy
gnrformatter vocabulary, already understood by the JS twin). Every
`^temperature` reader shows `39.2°`. Formulas are NOT affected: a
`data_formula` binding reading the same pointer receives the raw
`39.2` — presentation never leaks into computation.

## `_wdg` — exception attributes that travel with the datum

```python
data.set_item("temperature", 39.2, mask="%s°", _wdg={"color": "red"})
...
body.div("^temperature", color="gray")
```

`_wdg` is a dict of attributes the datum carries onto the element that
reads it as its value. On collision the datum **wins**: what travels
with the data is the exception (the alarm color), and the exception
beats the recipe's static default — the div is red, not gray.

## Template inputs — composed in the recipe, consumed, not emitted

```python
body.div("sized box", w="^box_width", width="${w}px", border="1px solid")
```

An attribute referenced by a `${...}` template of the same node is a
template input: the expansion consumes it and it is never emitted. The
name is free (`w`, `foo`); the usage, visible in the recipe, marks it.
This is the canonical idiom for "computed datum + authored unit" —
units are the author's responsibility, the framework never infers them.

## Output

See `output.html`.
