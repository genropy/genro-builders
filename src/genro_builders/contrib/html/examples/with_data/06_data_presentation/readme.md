# 06 — Data presentation

The datum knows how to present itself: presentation metadata lives on
the **data node**, and every element reading the datum renders it
accordingly — reactively, because the attributes survive value updates.

## `mask` — how the value is written

```python
data.set_item("temperature", 39.2, mask="%s°")
```

`mask` is a %-format whose single argument is the value: `%s` wraps
(`39.2°`), a numeric directive fixes the shape — `mask="%.2f"` shows
`45.00`, `mask="€ %.2f"` shows `€ 45.00` (the legacy gnrformatter
vocabulary). Every `^temperature` reader shows the masked value, the
value-only cell patches included: the wire carries what the render
shows. Formulas are NOT affected: a `data_formula` binding reading
the same pointer receives the raw `39.2` — presentation never leaks
into computation. A mask the value cannot honour (a numeric directive
on a string) raises: the datum declared a presentation it cannot
keep.

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
